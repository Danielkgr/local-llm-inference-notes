"""gen-hard-tasks.py reproduces tasks-hard.json byte for byte, and its needle
check fails loudly when a needle is missing or repeated."""

from __future__ import annotations

import shutil
import subprocess
import sys
from types import ModuleType

import pytest
from conftest import MODEL_EVAL, load_script


@pytest.fixture(scope="module")
def gen() -> ModuleType:
    return load_script(MODEL_EVAL / "gen-hard-tasks.py", "gen_hard_tasks")


def test_regeneration_is_byte_identical(tmp_path):
    # Run a copy, so the test never rewrites the committed file.
    script = tmp_path / "gen-hard-tasks.py"
    shutil.copy(MODEL_EVAL / "gen-hard-tasks.py", script)
    done = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True)
    assert "wrote" in done.stdout and "27 hard tasks" in done.stdout
    assert (tmp_path / "tasks-hard.json").read_bytes() == (
        MODEL_EVAL / "tasks-hard.json"
    ).read_bytes()


def test_import_does_not_write_and_renders_the_committed_file(gen):
    assert gen.render(gen.doc) == (MODEL_EVAL / "tasks-hard.json").read_text()


def test_assert_unique_accepts_exactly_one(gen):
    assert gen.assert_unique("port 41773 bound", "41773", "t") is None


@pytest.mark.parametrize(("hay", "count"), [("no needle here", 0), ("4417 and 4417", 2)])
def test_assert_unique_fails_loudly_otherwise(gen, hay, count):
    with pytest.raises(SystemExit) as exc:
        gen.assert_unique(hay, "4417" if count else "41773", "hard-longctx-99")
    assert "FATAL hard-longctx-99: needle" in str(exc.value.code)
    assert f"appears {count} times" in str(exc.value.code)


def test_task_ids_are_unique_and_all_hard(gen):
    ids = [t["id"] for t in gen.TASKS]
    assert len(ids) == len(set(ids)) == 27
    assert {t["tier"] for t in gen.TASKS} == {"hard"}
