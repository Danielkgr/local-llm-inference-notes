"""gen-hard-tasks.py reproduces tasks-hard.json byte for byte."""

from __future__ import annotations

import shutil
import subprocess
import sys

from conftest import MODEL_EVAL


def test_regeneration_is_byte_identical(tmp_path):
    # Run a copy, so the test never rewrites the committed file.
    script = tmp_path / "gen-hard-tasks.py"
    shutil.copy(MODEL_EVAL / "gen-hard-tasks.py", script)
    done = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True)
    assert "wrote" in done.stdout and "27 hard tasks" in done.stdout
    assert (tmp_path / "tasks-hard.json").read_bytes() == (
        MODEL_EVAL / "tasks-hard.json"
    ).read_bytes()
