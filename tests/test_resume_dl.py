"""resume-dl.py against a local HTTP server.

The tool's promise is that it can never truncate: it refuses to start without
a known size, and it refuses to append unless the server honoured the range.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conftest import TOOLS

SCRIPT = TOOLS / "resume-dl.py"


def cli(*args: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=timeout
    )


def test_refuses_to_start_without_a_known_size(file_server, tmp_path):
    file_server.head_length = False
    dest = tmp_path / "model.gguf"
    done = cli(file_server.url, str(dest))
    assert done.returncode == 1
    assert "could not determine size; refusing to run blind" in done.stderr
    assert not dest.exists()
    assert file_server.gets == 0


def test_resumes_a_partial_file_and_checks_the_magic(file_server, tmp_path):
    dest = tmp_path / "model.gguf"
    dest.write_bytes(file_server.content[:1000])
    done = cli(file_server.url, str(dest))
    assert done.returncode == 0, done.stderr
    assert dest.read_bytes() == file_server.content
    assert "resuming at 1000" in done.stdout
    assert "COMPLETE" in done.stdout


def test_refuses_to_append_when_the_range_is_ignored(file_server, tmp_path):
    file_server.honour_range = False
    dest = tmp_path / "model.gguf"
    partial = file_server.content[:1000]
    dest.write_bytes(partial)
    done = cli(file_server.url, str(dest))
    assert done.returncode == 1
    assert "resume not honoured (HTTP 200, expected 206)" in done.stderr
    # The bytes already on disk are untouched.
    assert dest.read_bytes() == partial


def test_expect_skips_the_head_request(file_server, tmp_path):
    file_server.head_length = False
    dest: Path = tmp_path / "model.gguf"
    done = cli(file_server.url, str(dest), "--expect", str(len(file_server.content)))
    assert done.returncode == 0, done.stderr
    assert dest.read_bytes() == file_server.content
