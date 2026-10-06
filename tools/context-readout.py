#!/usr/bin/env python3
"""How close are real chats to each model's configured context limit?

Context length is the easiest thing to over-buy.  A larger -c costs KV cache
memory on every load, and that memory competes with the weights for VRAM, so the
question "how much context do I actually use" is worth answering with data before
paying for headroom nobody reaches.

Cross-references three sources:
  1. each model's `-c` from a llama-swap config
  2. actual prompt sizes from Open WebUI chat history (read-only)
  3. live slot state from llama-swap's upstream proxy, for whatever is loaded

It reads only token COUNTS and model ids from the chat database.  No message
content is read, printed, or stored.

usage:
  context-readout.py [--chats N] [--config PATH] [--db PATH] [--endpoint URL]

env equivalents: LLAMA_SWAP_CONFIG, OPENWEBUI_DB, LLAMA_SWAP_URL

Incidental finding worth recording: llama-swap DOES expose the upstream `/props`
and `/slots`, but only under `/upstream/<url-encoded-model-id>/...`.  A bare
`/props` returns 404 "no model id could be identified" and `/slots` is not routed
at all.
"""

import argparse
import http.client
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request

DEF_CONF = os.environ.get(
    "LLAMA_SWAP_CONFIG", os.path.expanduser("~/.config/llama-swap/config.yaml")
)
DEF_DB = os.environ.get("OPENWEBUI_DB", os.path.expanduser("~/.open-webui/webui.db"))
DEF_SWAP = os.environ.get("LLAMA_SWAP_URL", "http://127.0.0.1:10000")


def configured_ctx(conf_path):
    """model id -> -c, plus alias -> canonical id."""
    import yaml

    with open(conf_path) as f:
        d = yaml.safe_load(f)
    ctx, alias = {}, {}
    for mid, m in (d.get("models") or {}).items():
        # Strip comment lines first: a config's own comments often contain strings
        # like "-c 16384 -> 65536 -> 131072", and a naive search returns the
        # historical value rather than the live one.
        cmd = "\n".join(
            line for line in m.get("cmd", "").splitlines() if not line.strip().startswith("#")
        )
        hit = re.findall(r"-c\s+(\d+)", cmd)
        ctx[mid] = int(hit[-1]) if hit else None
        for a in m.get("aliases") or []:
            alias[a] = mid
    return ctx, alias


def chat_stats(db_path, limit):
    """model id -> (last prompt tokens, max prompt tokens, n samples)."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    stats = {}
    rows = con.execute("select chat from chat order by updated_at desc limit ?", (limit,))
    for (blob,) in rows:
        try:
            c = json.loads(blob)
        except (ValueError, TypeError):  # not JSON, or a NULL chat column
            continue
        hist = (c.get("history") or {}).get("messages") or {}
        for m in hist.values():
            if m.get("role") != "assistant":
                continue
            u = m.get("usage") or {}
            n = u.get("prompt_n") or u.get("input_tokens")
            mid = m.get("model")
            if not n or not mid:
                continue
            last, mx, cnt = stats.get(mid, (None, 0, 0))
            stats[mid] = (n if last is None else last, max(mx, n), cnt + 1)
    return stats


def fetch_json(url, timeout):
    """Parsed JSON from url, or None when the server is down or the body is not JSON."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except (OSError, ValueError, http.client.HTTPException):
        return None


def live_slots(swap_url):
    """model id -> (n_slots, n_ctx, busy) for whatever is currently loaded."""
    out = {}
    run = fetch_json(swap_url + "/running", timeout=5)
    if not isinstance(run, dict):
        return out
    for r in run.get("running", []):
        mid = r.get("model")
        if not mid or r.get("state") != "ready":
            continue
        q = urllib.parse.quote(mid, safe="")
        s = fetch_json(f"{swap_url}/upstream/{q}/slots", timeout=8)
        if isinstance(s, list) and s:
            # NOTE: some llama.cpp builds expose only id / is_processing / n_ctx on
            # /slots, with no n_past, so a live "context fill" figure is not
            # available.  Report what is actually there rather than inventing a 0.
            busy = sum(1 for x in s if x.get("is_processing"))
            out[mid] = (len(s), s[0].get("n_ctx"), busy)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--chats", type=int, default=400, help="how many recent chats to scan (default 400)"
    )
    ap.add_argument("--config", default=DEF_CONF, help=f"llama-swap config (default {DEF_CONF})")
    ap.add_argument("--db", default=DEF_DB, help=f"Open WebUI database (default {DEF_DB})")
    ap.add_argument("--endpoint", default=DEF_SWAP, help=f"llama-swap URL (default {DEF_SWAP})")
    a = ap.parse_args()

    ctx, alias = configured_ctx(a.config)
    stats = chat_stats(a.db, a.chats)
    live = live_slots(a.endpoint)

    # fold alias-keyed history onto the canonical model id
    folded = {}
    for mid, v in stats.items():
        key = mid if mid in ctx else alias.get(mid, mid)
        if key in folded:
            l0, m0, c0 = folded[key]
            folded[key] = (l0 or v[0], max(m0, v[1]), c0 + v[2])
        else:
            folded[key] = v

    print(f"context readout -- {a.chats} most recent chats\n")
    print(f"{'model':44} {'-c':>8} {'last':>8} {'max':>8} {'max%':>6} {'turns':>6}")
    for mid in sorted(ctx):
        c = ctx[mid]
        last, mx, cnt = folded.get(mid, (None, 0, 0))
        pct = f"{mx / c * 100:5.1f}%" if c and mx else "     -"
        warn = ""
        if c and mx:
            if mx > c * 0.9:
                warn = "  <== OVER 90% of -c"
            elif mx > c * 0.7:
                warn = "  <== over 70%"
        print(
            f"{mid[:44]:44} {c or '?':>8} {last or '-':>8} {mx or '-':>8} {pct:>6} {cnt:>6}{warn}"
        )

    if live:
        print("\nlive (loaded now):")
        for mid, (nslots, nctx, busy) in live.items():
            print(f"  {mid[:44]:44} {nslots} slots x n_ctx {nctx}, {busy} busy")
    else:
        print("\nlive: no model currently loaded")

    unused = [m for m in ctx if m not in folded]
    if unused:
        print("\nno chat history recorded for: " + ", ".join(m[:30] for m in unused))
    print(
        "\nNote: 'max' is the largest single prompt seen, not a running total.  A chat "
        "grows\nuntil it hits -c, so a max well under -c means context is not the "
        "constraint."
    )


if __name__ == "__main__":
    main()
