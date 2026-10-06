"""run-eval.py end to end against a fake OpenAI-compatible server.

Covers the behaviours the notes depend on: an empty answer from a starved
token budget is its own error, never a pass or a content failure; the adoption
gate selects and orders tasks from a baseline file; the early abort refuses to
run where it could never fire; and a confirmed failure is retried once first.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import FakeModelServer, completion


def run(run_eval: ModuleType, monkeypatch: pytest.MonkeyPatch, *argv: str) -> None:
    monkeypatch.setattr(sys, "argv", ["run-eval.py", *argv])
    run_eval.main()


def write_baseline(path: Path, rows: list[dict[str, Any]], model: str = "incumbent") -> str:
    score = sum(1 for r in rows if r["pass"])
    doc = {"results": {model: {"score": score, "total": len(rows), "errors": 0, "rows": rows}}}
    path.write_text(json.dumps(doc))
    return str(path)


# Real core-tier ids, so selection runs against the shipped task files.
BASELINE_ROWS = [
    {"id": "extract-01", "pass": True, "secs": 5.0},
    {"id": "extract-02", "pass": True, "secs": 40.0},
    {"id": "extract-04", "pass": True, "secs": 20.0},
    {"id": "instruct-01", "pass": False, "secs": 30.0},
    {"id": "faith-03", "pass": False, "secs": 10.0},
]


def dry_run_ids(out: str) -> list[str]:
    """The task ids a --dry-run printed, in run order."""
    lines = out.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("dry-run --"))
    ids = []
    for line in lines[start + 1 :]:
        if not line.startswith("  "):
            break
        ids.append(line.split()[0])
    return ids


# ------------------------------------------------------------------ token starvation
def test_starved_budget_is_an_error_not_a_failure(
    run_eval, monkeypatch, capsys, model_server, tmp_path
):
    def reply(model: str, task_id: str):
        if task_id == "extract-01":
            return completion("", finish="length", reasoning="x" * 1234)
        return completion("192.0.2.147")

    model_server.reply = reply
    out_file = tmp_path / "run.json"
    run(
        run_eval,
        monkeypatch,
        "--endpoint", model_server.endpoint,
        "--models", "model-a",
        "--only", "extract-01,extract-02",
        "--out", str(out_file),
    )  # fmt: skip

    doc = json.loads(out_file.read_text())
    result = doc["results"]["model-a"]
    rows = {r["id"]: r for r in result["rows"]}
    assert result["score"] == 1
    assert result["errors"] == 1
    assert rows["extract-01"]["pass"] is False
    assert rows["extract-01"]["why"] == "EMPTY (finish=length, reasoning=1234c)"
    assert rows["extract-02"]["pass"] is True
    # The budget that produced the run is recorded with it.
    assert doc["settings"]["max_tokens"] == 16000
    printed = capsys.readouterr().out
    assert "ERR   extract-01" in printed
    assert "FAIL  extract-01" not in printed


@pytest.mark.parametrize("jobs", ["1", "2"])
def test_error_body_is_an_api_error_and_the_run_continues(
    run_eval, monkeypatch, model_server, tmp_path, jobs
):
    def reply(model: str, task_id: str):
        if task_id == "extract-01":
            return 200, {"error": {"code": 500, "message": "model failed to load"}}
        if task_id == "extract-02":
            return 200, {"choices": []}
        return completion("acknowledged")

    model_server.reply = reply
    out_file = tmp_path / "run.json"
    run(
        run_eval,
        monkeypatch,
        "--endpoint", model_server.endpoint,
        "--models", "model-a",
        "--only", "extract-01,extract-02,instruct-01",
        "--jobs", jobs,
        "--out", str(out_file),
    )  # fmt: skip
    result = json.loads(out_file.read_text())["results"]["model-a"]
    rows = {r["id"]: r for r in result["rows"]}
    assert rows["extract-01"]["why"] == "API: error body: model failed to load"
    assert rows["extract-02"]["why"].startswith("API: no choices in response")
    assert rows["instruct-01"]["pass"] is True
    assert result["errors"] == 2


# --------------------------------------------------------------- gate selection
def test_gate_passed_selects_only_tasks_the_baseline_passed(
    run_eval, monkeypatch, capsys, tmp_path
):
    base = write_baseline(tmp_path / "base.json", BASELINE_ROWS)
    run(
        run_eval, monkeypatch, "--tier", "core", "--baseline", base, "--gate", "passed", "--dry-run"
    )
    out = capsys.readouterr().out
    assert dry_run_ids(out) == ["extract-01", "extract-02", "extract-04"]
    # Tasks the baseline never ran are reported, not silently dropped.
    assert "warning: 18 task(s) not in the baseline, excluded from --gate passed" in out


def test_gate_failed_selects_only_tasks_the_baseline_failed(
    run_eval, monkeypatch, capsys, tmp_path
):
    base = write_baseline(tmp_path / "base.json", BASELINE_ROWS)
    run(
        run_eval, monkeypatch, "--tier", "core", "--baseline", base, "--gate", "failed", "--dry-run"
    )
    assert dry_run_ids(capsys.readouterr().out) == ["instruct-01", "faith-03"]


def test_order_baseline_slowest_puts_expensive_tasks_first(run_eval, monkeypatch, capsys, tmp_path):
    base = write_baseline(tmp_path / "base.json", BASELINE_ROWS)
    run(
        run_eval,
        monkeypatch,
        "--tier", "core",
        "--baseline", base,
        "--gate", "passed",
        "--order", "baseline-slowest",
        "--dry-run",
    )  # fmt: skip
    assert dry_run_ids(capsys.readouterr().out) == ["extract-02", "extract-04", "extract-01"]


def test_early_abort_refuses_concurrency(run_eval, monkeypatch, tmp_path):
    base = write_baseline(tmp_path / "base.json", BASELINE_ROWS)
    with pytest.raises(SystemExit) as exc:
        run(
            run_eval,
            monkeypatch,
            "--baseline", base,
            "--gate", "passed",
            "--gate-stop-after", "2",
            "--jobs", "2",
            "--dry-run",
        )  # fmt: skip
    assert "--gate-stop-after needs --jobs 1" in str(exc.value.code)


def test_gate_requires_a_baseline(run_eval, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run(run_eval, monkeypatch, "--gate", "passed", "--dry-run")
    assert "require --baseline" in str(exc.value.code)


def test_gate_refuses_an_ambiguous_baseline(run_eval, monkeypatch, tmp_path):
    rows = BASELINE_ROWS
    doc = {
        "results": {
            m: {"score": 3, "total": len(rows), "errors": 0, "rows": rows} for m in ("one", "two")
        }
    }
    base = tmp_path / "two-models.json"
    base.write_text(json.dumps(doc))
    with pytest.raises(SystemExit) as exc:
        run(run_eval, monkeypatch, "--baseline", str(base), "--gate", "passed", "--dry-run")
    assert "--gate-model" in str(exc.value.code)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "cannot read"),
        ("{not json", "is not valid JSON"),
        ('{"when": "yesterday"}', "has no results, so it is not a run-eval.py results file"),
        (
            '{"results": {"m": {"score": 1, "total": 1, "rows": [{"id": "x"}]}}}',
            "need score, total",
        ),
    ],
)
def test_unusable_baseline_is_a_clear_error(run_eval, monkeypatch, tmp_path, content, message):
    path = tmp_path / "baseline.json"
    if content is not None:
        path.write_text(content)
    with pytest.raises(SystemExit) as exc:
        run(run_eval, monkeypatch, "--baseline", str(path), "--gate", "passed", "--dry-run")
    assert message in str(exc.value.code)


@pytest.mark.parametrize(
    ("value", "message"),
    [("{enable_thinking: false}", "not valid JSON"), ("[1, 2]", "must be a JSON object")],
)
def test_unusable_chat_kwargs_is_a_usage_error(run_eval, monkeypatch, capsys, value, message):
    with pytest.raises(SystemExit) as exc:
        run(run_eval, monkeypatch, "--chat-kwargs", value, "--dry-run")
    assert exc.value.code == 2
    assert message in capsys.readouterr().err


# --------------------------------------------------------------- gate in a real run
def test_gate_retries_then_aborts_on_confirmed_new_failures(
    run_eval, monkeypatch, capsys, model_server, tmp_path
):
    base = write_baseline(tmp_path / "base.json", BASELINE_ROWS[:3])

    def reply(model: str, task_id: str):
        return completion("137" if task_id == "extract-04" else "wrong")

    model_server.reply = reply
    out_file = tmp_path / "gate.json"
    run(
        run_eval,
        monkeypatch,
        "--endpoint", model_server.endpoint,
        "--models", "model-a",
        "--tier", "core",
        "--baseline", base,
        "--gate", "passed",
        "--gate-stop-after", "2",
        "--out", str(out_file),
    )  # fmt: skip

    # Each new failure is retried once before it counts, and the third task never runs.
    assert model_server.count("extract-01") == 2
    assert model_server.count("extract-02") == 2
    assert model_server.count("extract-04") == 0
    doc = json.loads(out_file.read_text())
    result = doc["results"]["model-a"]
    assert result["new_failures"] == ["extract-01", "extract-02"]
    assert result["aborted"].startswith("2 confirmed new failure(s)")
    # A partial run says so in its own output.
    assert doc["selection"]["complete_suite"] is False
    assert doc["selection"]["gate"] == "passed"
    assert "PARTIAL RUN" in capsys.readouterr().out


@pytest.mark.parametrize("jobs", ["1", "2"])
def test_each_model_is_scored_on_its_own_answers(
    run_eval, monkeypatch, model_server, tmp_path, jobs
):
    # model-a answers correctly and model-b does not, so any mix-up of which model a
    # task was sent to shows up as the wrong score.
    model_server.reply = lambda model, task_id: completion(
        "acknowledged" if model == "model-a" else "refused"
    )
    out_file = tmp_path / "two.json"
    run(
        run_eval,
        monkeypatch,
        "--endpoint", model_server.endpoint,
        "--models", "model-a,model-b",
        "--only", "instruct-01,extract-01",
        "--jobs", jobs,
        "--out", str(out_file),
    )  # fmt: skip
    results = json.loads(out_file.read_text())["results"]
    assert results["model-a"]["score"] == 1
    assert results["model-b"]["score"] == 0
    assert sorted(model_server.requests) == [
        ("model-a", "extract-01"),
        ("model-a", "instruct-01"),
        ("model-b", "extract-01"),
        ("model-b", "instruct-01"),
    ]


# ----------------------------------------------------------- model names with commas
def test_comma_list_of_served_models_is_split(run_eval, monkeypatch, model_server, tmp_path):
    out_file = tmp_path / "two.json"
    run(
        run_eval,
        monkeypatch,
        "--endpoint", model_server.endpoint,
        "--models", "model-a,model-b",
        "--only", "instruct-01",
        "--out", str(out_file),
    )  # fmt: skip
    assert sorted(json.loads(out_file.read_text())["results"]) == ["model-a", "model-b"]


def test_served_name_containing_a_comma_is_taken_whole(run_eval, monkeypatch, tmp_path):
    name = "08. Model-A-27B (variant-tag, MTP Q4_K_M)"
    server = FakeModelServer(served=[name])
    try:
        out_file = tmp_path / "one.json"
        run(
            run_eval,
            monkeypatch,
            "--endpoint", server.endpoint,
            "--models", name,
            "--only", "instruct-01",
            "--out", str(out_file),
        )  # fmt: skip
        assert list(json.loads(out_file.read_text())["results"]) == [name]
        assert server.count("instruct-01") == 1
    finally:
        server.close()


# ------------------------------------------------------------------ model list URL
@pytest.mark.parametrize(
    ("endpoint", "want"),
    [
        ("http://127.0.0.1:10000/v1/chat/completions", "http://127.0.0.1:10000/v1/models"),
        ("http://host:3000/api/chat/completions", "http://host:3000/api/models"),
        ("http://host:8080/chat/completions", "http://host:8080/models"),
        ("http://host:8080/v1/chat/completions/", "http://host:8080/v1/models"),
        ("http://host:8080/v1/completions", "http://host:8080/v1/models"),
        ("http://host/generate", None),
    ],
)
def test_models_url(run_eval, endpoint, want):
    assert run_eval.models_url(endpoint) == want


def test_endpoint_without_v1_is_discovered(run_eval, monkeypatch, model_server, tmp_path):
    out_file = tmp_path / "api.json"
    run(
        run_eval,
        monkeypatch,
        "--endpoint", model_server.base + "/api/chat/completions",
        "--models", "model-a",
        "--only", "instruct-01",
        "--out", str(out_file),
    )  # fmt: skip
    assert list(json.loads(out_file.read_text())["results"]) == ["model-a"]
    assert model_server.count("instruct-01") == 1


def test_endpoint_with_no_model_list_is_a_clear_error(run_eval, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run(
            run_eval,
            monkeypatch,
            "--endpoint",
            "http://127.0.0.1:9/generate",
            "--only",
            "instruct-01",
        )
    assert "cannot work out the model-list URL" in str(exc.value.code)


def test_every_flag_has_help(run_eval):
    missing = [a.option_strings for a in run_eval.build_parser()._actions if not a.help]
    assert not missing
