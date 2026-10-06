#!/usr/bin/env python3
"""Downloader that cannot truncate: append-only, verifies 206 before resuming."""

import argparse
import os
import sys
import time
import urllib.error
import urllib.request

CHUNK = 1 << 20
UA = {"User-Agent": "resume-dl/1.0"}
# 408 and 429 ask the client to come back later, so they are worth waiting out.  Any
# other 4xx gives the same answer on every attempt: retrying a 404 500 times, with
# back-off, spends hours and hides the real error.
RETRYABLE_CLIENT_ERRORS = {408, 429}


def retryable(e):
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500 or e.code in RETRYABLE_CLIENT_ERRORS
    return True


def head_size(url):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        n = r.headers.get("Content-Length")
        return int(n) if n else 0


def attempt(url, dest, total, log):
    have = os.path.getsize(dest) if os.path.exists(dest) else 0
    if total and have >= total:
        return have, True
    headers = dict(UA)
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        code = r.getcode()
        if have and code != 206:
            raise RuntimeError(
                f"resume not honoured (HTTP {code}, expected 206). "
                f"Refusing to touch the existing {have} bytes."
            )
        if not have and code not in (200, 206):
            raise RuntimeError(f"unexpected HTTP {code}")
        log(
            f"  resuming at {have} ({r.headers.get('Content-Range')})"
            if code == 206
            else f"  starting fresh (HTTP {code})"
        )
        last, start_bytes = time.time(), have
        with open(dest, "ab") as f:
            while True:
                buf = r.read(CHUNK)
                if not buf:
                    break
                f.write(buf)
                have += len(buf)
                now = time.time()
                if now - last >= 30:
                    rate = (have - start_bytes) / (now - last) / 1e6
                    log(
                        f"  {have / 1e9:.2f} / {total / 1e9:.2f} GB "
                        f"({have / total * 100:.1f}%) {rate:.1f} MB/s"
                    )
                    last, start_bytes = now, have
    return have, bool(total and have >= total)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Resume a large download without ever truncating the partial file."
    )
    ap.add_argument("url", metavar="URL", help="the file to download")
    ap.add_argument(
        "dest",
        metavar="DEST",
        help="local path; an existing partial file is resumed, never rewritten",
    )
    ap.add_argument(
        "--expect",
        type=int,
        metavar="BYTES",
        help="the final size in bytes, which skips the HEAD request that otherwise finds it",
    )
    a = ap.parse_args(argv)
    url, dest, expect = a.url, a.dest, a.expect

    def log(m):
        print(f"{time.strftime('%H:%M:%S')} {m}", flush=True)

    if expect:
        total = expect
    else:
        try:
            total = head_size(url)
        except (urllib.error.URLError, OSError) as e:
            sys.exit(
                f"ERROR: could not determine size ({e}); refusing to run blind.  "
                "Pass --expect BYTES if the server will not answer HEAD."
            )
    if not total:
        sys.exit("ERROR: could not determine size; refusing to run blind.")
    log(f"target {total} bytes -> {dest}")
    tries = 0
    while True:
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        if have >= total:
            break
        try:
            have, done = attempt(url, dest, total, log)
            tries = 0
            if done:
                break
        except RuntimeError as e:
            sys.exit(f"FATAL: {e}")
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            if not retryable(e):
                sys.exit(f"FATAL: {e}; a client error will not change on retry.")
            tries += 1
            if tries > 500:
                sys.exit(f"giving up after {tries} retries: {e}")
            log(f"  retry {tries}: {e}")
            time.sleep(min(5 * tries, 60))
    final = os.path.getsize(dest)
    if final != total:
        sys.exit(f"ERROR: size {final} != expected {total}")
    with open(dest, "rb") as f:
        magic = f.read(4)
    log(f"COMPLETE {final} bytes, magic={magic!r}")
    if dest.endswith(".gguf") and magic != b"GGUF":
        sys.exit("ERROR: bad GGUF magic, file is corrupt.")


if __name__ == "__main__":
    main()
