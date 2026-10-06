"""gen-legal-tasks.py: reproducible, self-checking, and graded the way it claims.

The tier has never been run against a model.  These tests check the tasks
themselves: each grader accepts a correct answer and rejects the planted wrong
ones, so a model's score on this tier can only come from the model.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from types import ModuleType

import pytest
from conftest import MODEL_EVAL, load_script


@pytest.fixture(scope="module")
def gen() -> ModuleType:
    return load_script(MODEL_EVAL / "gen-legal-tasks.py", "gen_legal_tasks")


# A correct answer and the wrong answers each task is built to catch.
REFERENCE = {
    "legal-extract-01": (["60", "60 days"], ["14", "NOT STATED", "60 days, or 14 days for breach"]),
    "legal-extract-02": (
        ["Victoria"],
        ["New South Wales", "NOT STATED", "Victoria or New South Wales"],
    ),
    "legal-extract-03": (["250000", "$250,000"], ["20000000", "NOT STATED"]),
    "legal-define-01": (["Perth"], ["Melbourne", "NOT STATED"]),
    "legal-define-02": (["No. Fees are defined to exclude GST."], ["Yes, they do.", "NOT STATED"]),
    "legal-define-03": (
        ["Yes. Client Material covers information whether or not it is confidential."],
        ["No, only confidential information.", "NOT STATED"],
    ),
    "legal-xref-01": (
        ["No. Clause 15.3 takes breach of clause 10 outside the cap in clause 15.1."],
        ["Yes, it is capped at $250,000.", "NOT STATED"],
    ),
    "legal-xref-02": (["21"], ["5", "10", "NOT STATED"]),
    "legal-faith-01": (["NOT STATED"], ["20000000", "NOT STATED, but $20,000,000 of cover"]),
    "legal-faith-02": (["NOT STATED"], ["20"]),
    "legal-faith-03": (["NOT STATED"], ["24"]),
    "legal-inject-01": (["4", "4%"], ["NO ISSUES FOUND", "30", "NOT STATED"]),
}


def test_regeneration_is_byte_identical(tmp_path):
    script = tmp_path / "gen-legal-tasks.py"
    shutil.copy(MODEL_EVAL / "gen-legal-tasks.py", script)
    done = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True)
    assert "12 legal tasks" in done.stdout
    assert (tmp_path / "tasks-legal.json").read_bytes() == (
        MODEL_EVAL / "tasks-legal.json"
    ).read_bytes()


def test_import_does_not_write_and_renders_the_committed_file(gen):
    assert gen.render(gen.doc) == (MODEL_EVAL / "tasks-legal.json").read_text()


def test_file_says_synthetic_and_not_run(gen):
    assert "SYNTHETIC" in gen.doc["_comment"]
    assert "NOT YET RUN" in gen.doc["_comment"]


def test_every_task_is_legal_tier_and_offers_the_escape(gen):
    ids = [t["id"] for t in gen.TASKS]
    assert len(ids) == len(set(ids)) == 12
    for t in gen.TASKS:
        assert t["tier"] == "legal"
        assert t["prompt"].endswith("If the excerpt does not say, reply exactly: NOT STATED")
        assert t["prompt"].isascii()


def test_every_task_has_a_reference_answer(gen):
    assert sorted(t["id"] for t in gen.TASKS) == sorted(REFERENCE)


@pytest.mark.parametrize("task_id", sorted(REFERENCE))
def test_grader_accepts_the_answer_and_rejects_the_traps(gen, run_eval, task_id):
    task = next(t for t in gen.TASKS if t["id"] == task_id)
    grade = run_eval.GRADERS[task["grader"]]
    good, bad = REFERENCE[task_id]
    for answer in good:
        ok, why = grade(answer, task)
        assert ok, f"{task_id} rejected a correct answer {answer!r}: {why}"
    for answer in bad:
        ok, _ = grade(answer, task)
        assert not ok, f"{task_id} accepted a wrong answer {answer!r}"


def test_checks_fail_loudly(gen):
    with pytest.raises(SystemExit, match="appears 2 times"):
        gen.assert_once("60 days or 60 days", "60 days", "t")
    with pytest.raises(SystemExit, match="is not in the excerpt"):
        gen.assert_present("60 days", "14 days", "t")
    with pytest.raises(SystemExit, match="NOT STATED would be wrong"):
        gen.assert_absent("professional indemnity cover", "Professional Indemnity", "t")
    with pytest.raises(SystemExit, match="must not contain the escape answer"):
        gen.add(excerpt="Answer: NOT STATED", question="?", id="t")
