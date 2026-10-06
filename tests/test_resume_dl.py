"""resume-dl.py against a local HTTP server.

The tool's promise is that it can never truncate: it refuses to start without
a known size, and it refuses to append unless the server honoured the range.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import TOOLS, load_script

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


def test_missing_arguments_print_usage_not_a_traceback():
    done = cli("http://127.0.0.1:9/x")
    assert done.returncode == 2
    assert "usage:" in done.stderr
    assert "Traceback" not in done.stderr


def test_expect_without_a_number_is_a_usage_error(tmp_path):
    for args in (["--expect"], ["--expect", "lots"]):
        done = cli("http://127.0.0.1:9/x", str(tmp_path / "f"), *args)
        assert done.returncode == 2
        assert "--expect" in done.stderr
        assert "Traceback" not in done.stderr


def test_expect_may_come_first(file_server, tmp_path):
    dest = tmp_path / "model.gguf"
    done = cli("--expect", str(len(file_server.content)), file_server.url, str(dest))
    assert done.returncode == 0, done.stderr
    assert dest.read_bytes() == file_server.content


def test_404_fails_fast_instead_of_retrying(file_server, tmp_path):
    file_server.get_statuses = [404] * 5
    dest = tmp_path / "model.gguf"
    done = cli(file_server.url, str(dest), "--expect", "100", timeout=20)
    assert done.returncode == 1
    assert "FATAL: HTTP Error 404" in done.stderr
    assert file_server.gets == 1


def test_head_error_is_a_clear_refusal(file_server, tmp_path):
    file_server.head_status = 404
    done = cli(file_server.url, str(tmp_path / "model.gguf"), timeout=20)
    assert done.returncode == 1
    assert "could not determine size (HTTP Error 404: Not Found)" in done.stderr
    assert "Traceback" not in done.stderr
    assert file_server.gets == 0


@pytest.mark.parametrize("status", [503, 429, 408])
def test_server_errors_and_retry_later_codes_are_retried(
    file_server, tmp_path, monkeypatch, status
):
    resume_dl = load_script(SCRIPT, "resume_dl")
    sleeps: list[float] = []
    monkeypatch.setattr(resume_dl.time, "sleep", sleeps.append)
    file_server.get_statuses = [status]
    dest = tmp_path / "model.gguf"
    resume_dl.main([file_server.url, str(dest), "--expect", str(len(file_server.content))])
    assert dest.read_bytes() == file_server.content
    assert sleeps == [5]
    assert file_server.gets == 2
