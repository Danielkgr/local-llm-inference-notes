"""Every deterministic grader in run-eval.py, seen to pass and seen to fail.

A grader that has never been seen to fail has not been tested, so each case
below pairs an answer the grader must accept with one it must reject.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

import pytest
from conftest import all_tasks

CASES: list[tuple[str, dict[str, Any], str, bool]] = [
    # substring: every expected string, case-insensitively, and no reject string
    ("contains_all", {"expect": ["1488.00"], "reject": ["1240"]}, "The total is 1488.00", True),
    ("contains_all", {"expect": ["1488.00"], "reject": ["1240"]}, "1240.00", False),
    ("contains_all", {"expect": ["1488.00"], "reject": ["1240"]}, "1488.00, not 1240.00", False),
    ("contains_all", {"expect": ["NOT STATED"]}, "not stated", True),
    # an empty expect list passes exactly when no reject string appears
    ("contains_all", {"expect": [], "reject": ["token"]}, "It predicts several", True),
    ("contains_all", {"expect": [], "reject": ["token"]}, "It predicts tokens", False),
    # regex: case-insensitive search, reject patterns checked first
    ("regex", {"expect": [r"\b137\b"]}, "exit code 137", True),
    ("regex", {"expect": [r"\b137\b"]}, "exit code 1370", False),
    ("regex", {"expect": [r"\b3000\b"], "reject": ["8080"]}, "3000 (not 8080)", False),
    ("regex", {"expect": [r"\[1\]", r"\[1,\s*2\]"]}, "[1]\n[1, 2]", True),
    # starts_with_any: leading non-letters are stripped first
    ("starts_with_any", {"expect": ["no"]}, "**No.**  It does not fit.", True),
    ("starts_with_any", {"expect": ["no"]}, "Yes, it fits.", False),
    # numeric: any number in the output within the tolerance
    ("numeric", {"expect": [7.8], "tolerance": 0.2}, "About 7.9 GB", True),
    ("numeric", {"expect": [7.8], "tolerance": 0.2}, "8.1", False),
    ("numeric", {"expect": [41773], "tolerance": 0}, "41,773", True),
    ("numeric", {"expect": [2.46]}, "no digits here", False),
    # exact word: letters only, case-insensitive
    ("exact_word", {"expect": ["acknowledged"]}, "Acknowledged.", True),
    ("exact_word", {"expect": ["acknowledged"]}, "acknowledged, thanks", False),
    # word count within a tolerance
    ("word_count", {"expect": [3], "tolerance": 1}, "Blue, mostly clear", True),
    ("word_count", {"expect": [7], "tolerance": 0}, "One two three four five six", False),
    # JSON key presence, with or without a markdown fence
    (
        "json_keys",
        {"expect": ["host", "port"]},
        '```json\n{"host": "box", "port": 8080}\n```',
        True,
    ),
    ("json_keys", {"expect": ["host", "port"]}, '{"host": "box"}', False),
    ("json_keys", {"expect": ["host"]}, "{host: box}", False),
    ("json_keys", {"expect": ["host"]}, "no object at all", False),
    # any key term, and short
    (
        "contains_any_and_short",
        {"expect": ["kernel"], "max_words": 5},
        "Kernel 7.0 hung renders.",
        True,
    ),
    ("contains_any_and_short", {"expect": ["kernel"], "max_words": 5}, "Renders hung.", False),
    (
        "contains_any_and_short",
        {"expect": ["kernel"], "max_words": 5},
        "The kernel update made every single render hang.",
        False,
    ),
]


@pytest.mark.parametrize(("grader", "task", "output", "want"), CASES)
def test_grader(run_eval: ModuleType, grader: str, task: dict[str, Any], output: str, want: bool):
    ok, why = run_eval.GRADERS[grader](output, task)
    assert ok is want, why
    assert isinstance(why, str) and why


def test_every_grader_has_a_pass_and_a_fail_case(run_eval: ModuleType):
    covered = {(g, want) for g, _, _, want in CASES}
    for name in run_eval.GRADERS:
        assert (name, True) in covered and (name, False) in covered, name


def test_every_task_names_a_known_grader(run_eval: ModuleType):
    unknown = {t["id"]: t["grader"] for t in all_tasks() if t["grader"] not in run_eval.GRADERS}
    assert not unknown
