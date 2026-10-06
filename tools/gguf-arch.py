#!/usr/bin/env python3
"""Print a GGUF file's general.architecture (and a few shape keys) from the header.

Why this exists: `llama-gguf <file> r n` prints KV *keys* but not their string
values, so grepping it for the architecture silently yields an empty string --
which turns an architecture gate into a gate that passes everything. This reads
the header bytes directly instead.

  gguf-arch.py FILE            -> "qwen35moe"
  gguf-arch.py FILE --all      -> arch plus block_count / expert_count / context_length
"""

import argparse
import os
import struct
import sys

T_UINT8, T_INT8, T_UINT16, T_INT16, T_UINT32, T_INT32 = 0, 1, 2, 3, 4, 5
T_FLOAT32, T_BOOL, T_STRING, T_ARRAY, T_UINT64, T_INT64, T_FLOAT64 = 6, 7, 8, 9, 10, 11, 12
FIXED = {
    T_UINT8: 1,
    T_INT8: 1,
    T_UINT16: 2,
    T_INT16: 2,
    T_UINT32: 4,
    T_INT32: 4,
    T_FLOAT32: 4,
    T_BOOL: 1,
    T_UINT64: 8,
    T_INT64: 8,
    T_FLOAT64: 8,
}
SFMT = {
    T_UINT8: "B",
    T_INT8: "b",
    T_UINT16: "H",
    T_INT16: "h",
    T_UINT32: "I",
    T_INT32: "i",
    T_FLOAT32: "f",
    T_BOOL: "?",
    T_UINT64: "Q",
    T_INT64: "q",
    T_FLOAT64: "d",
}


class R:
    def __init__(self, f):
        self.f = f
        self.size = os.fstat(f.fileno()).st_size

    def raw(self, n):
        # A corrupt length field can claim exabytes.  Refuse before reading rather than
        # asking for the allocation, so a bad file is reported as truncated.
        if n > self.size - self.f.tell():
            raise EOFError("truncated GGUF header")
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError("truncated GGUF header")
        return b

    def u32(self):
        return struct.unpack("<I", self.raw(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.raw(8))[0]

    def s(self):
        return self.raw(self.u64()).decode("utf-8", "replace")

    def value(self, t):
        if t == T_STRING:
            return self.s()
        if t in FIXED:
            return struct.unpack("<" + SFMT[t], self.raw(FIXED[t]))[0]
        if t == T_ARRAY:
            et, n = self.u32(), self.u64()
            if et == T_STRING:
                for _ in range(n):
                    self.s()
            elif et == T_ARRAY:
                raise ValueError("nested array")
            elif et not in FIXED:
                raise ValueError(f"unknown array element type {et}")
            else:
                self.raw(FIXED[et] * n)
            return f"<array[{n}]>"
        raise ValueError(f"unknown value type {t}")


def read_kv(path, wanted=None, limit=None):
    out = {}
    with open(path, "rb") as f:
        r = R(f)
        if r.raw(4) != b"GGUF":
            raise ValueError("not a GGUF file")
        r.u32()  # version
        r.u64()  # tensor count
        n_kv = r.u64()
        for _ in range(n_kv):
            k = r.s()
            v = r.value(r.u32())
            if wanted is None or any(k.endswith(w) or k == w for w in wanted):
                out[k] = v
            if limit and len(out) >= limit:
                break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Print a GGUF file's general.architecture, read from the header bytes."
    )
    ap.add_argument("path", metavar="FILE", help="the .gguf file to read")
    ap.add_argument(
        "--all",
        action="store_true",
        help="also print block_count, expert_count, context_length, and the other shape keys",
    )
    a = ap.parse_args(argv)
    try:
        kv = read_kv(a.path)
    except (OSError, EOFError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    arch = kv.get("general.architecture", "")
    if not arch:
        print("ERROR: general.architecture absent", file=sys.stderr)
        return 3
    print(arch)
    if not a.all:
        return 0
    for suffix in (
        "block_count",
        "expert_count",
        "expert_used_count",
        "context_length",
        "nextn_predict_layers",
        "full_attention_interval",
    ):
        for k, v in kv.items():
            if k.endswith("." + suffix):
                print(f"{suffix}={v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
