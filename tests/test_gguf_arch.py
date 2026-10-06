"""gguf-arch.py against GGUF headers built by hand.

The header layout follows the GGUF format: the magic "GGUF", a uint32 version,
a uint64 tensor count, a uint64 key/value count, then each key as a uint64
length-prefixed string, a uint32 value type, and the value.
"""

from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

from conftest import TOOLS

T_UINT32, T_FLOAT32, T_BOOL, T_STRING, T_ARRAY = 4, 6, 7, 8, 9
SCRIPT = TOOLS / "gguf-arch.py"


def gguf_string(s: str) -> bytes:
    b = s.encode()
    return struct.pack("<Q", len(b)) + b


def gguf_value(vtype: int, value: Any) -> bytes:
    if vtype == T_STRING:
        return gguf_string(value)
    if vtype == T_UINT32:
        return struct.pack("<I", value)
    if vtype == T_FLOAT32:
        return struct.pack("<f", value)
    if vtype == T_BOOL:
        return struct.pack("<?", value)
    if vtype == T_ARRAY:
        etype, items = value
        return struct.pack("<IQ", etype, len(items)) + b"".join(gguf_value(etype, i) for i in items)
    raise ValueError(vtype)


def gguf_header(kvs: list[tuple[str, int, Any]], magic: bytes = b"GGUF") -> bytes:
    out = magic + struct.pack("<IQQ", 3, 0, len(kvs))
    for key, vtype, value in kvs:
        out += gguf_string(key) + struct.pack("<I", vtype) + gguf_value(vtype, value)
    return out


MODEL_KVS = [
    ("general.architecture", T_STRING, "llama"),
    ("general.name", T_STRING, "test model"),
    ("tokenizer.ggml.tokens", T_ARRAY, (T_STRING, ["<s>", "</s>", "hello"])),
    ("tokenizer.ggml.scores", T_ARRAY, (T_FLOAT32, [0.0, 0.5, 1.0])),
    ("llama.block_count", T_UINT32, 32),
    ("llama.context_length", T_UINT32, 8192),
    ("llama.expert_count", T_UINT32, 8),
    ("llama.rope.freq_base", T_FLOAT32, 10000.0),
    ("general.quantized", T_BOOL, True),
]


def write(tmp_path: Path, data: bytes, name: str = "model.gguf") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_read_kv_skips_arrays_and_reads_scalars(gguf_arch, tmp_path):
    kv = gguf_arch.read_kv(write(tmp_path, gguf_header(MODEL_KVS)))
    assert kv["general.architecture"] == "llama"
    assert kv["tokenizer.ggml.tokens"] == "<array[3]>"
    assert kv["llama.block_count"] == 32
    assert kv["general.quantized"] is True


def test_prints_the_architecture(tmp_path):
    done = cli(str(write(tmp_path, gguf_header(MODEL_KVS))))
    assert done.returncode == 0
    assert done.stdout == "llama\n"


def test_all_prints_the_shape_keys_with_their_values(tmp_path):
    done = cli(str(write(tmp_path, gguf_header(MODEL_KVS))), "--all")
    assert done.returncode == 0
    assert done.stdout.splitlines() == [
        "llama",
        "block_count=32",
        "expert_count=8",
        "context_length=8192",
    ]


def test_wrong_magic_is_an_error(tmp_path):
    done = cli(str(write(tmp_path, gguf_header(MODEL_KVS, magic=b"GGML"))))
    assert done.returncode == 2
    assert "not a GGUF file" in done.stderr


def test_truncated_header_is_an_error(tmp_path):
    data = gguf_header(MODEL_KVS)
    done = cli(str(write(tmp_path, data[: len(data) // 2])))
    assert done.returncode == 2
    assert "truncated GGUF header" in done.stderr


def test_missing_architecture_is_its_own_exit_code(tmp_path):
    kvs = [kv for kv in MODEL_KVS if kv[0] != "general.architecture"]
    done = cli(str(write(tmp_path, gguf_header(kvs))))
    assert done.returncode == 3
    assert "general.architecture absent" in done.stderr
