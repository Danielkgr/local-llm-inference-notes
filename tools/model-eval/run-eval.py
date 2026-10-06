#!/usr/bin/env python3
"""
run-eval.py -- graded eval suite for a local OpenAI-compatible model server.

Answers "is model A better than model B for my work" with a number instead of a
feeling, and catches silent regressions after template, sampling, or system-prompt
changes.

  ./run-eval.py                            # every model the server advertises
  ./run-eval.py --models "my-model"        # one or more, comma separated
  ./run-eval.py --category code            # one category
  ./run-eval.py --tier core                # the 23 original tasks only
  ./run-eval.py --baseline FILE.json       # compare against a previous run
  ./run-eval.py --no-system                # ignore the prose system prompt
  ./run-eval.py --endpoint http://host:8080/v1/chat/completions

Adoption gate -- run only the tasks that can actually decide it:

  ./run-eval.py --models CANDIDATE --baseline incumbent.json \
                --gate passed --order baseline-slowest --gate-stop-after 2
  ./run-eval.py --models CANDIDATE --baseline incumbent.json --gate failed

Works against anything speaking the OpenAI chat-completions API: llama.cpp's
llama-server, llama-swap, vLLM, Ollama's compatibility endpoint.

Design decisions that matter:
  * Graders are DETERMINISTIC (substring / regex / numeric / JSON). An LLM judge
    would make the measurement depend on the thing being measured.
  * max_tokens is GENEROUS. Reasoning models spend their budget on
    reasoning_content first; at 420 tokens three different models returned
    content='' with finish_reason='length'. Empty content is scored as an ERROR,
    never a pass and never a content failure -- an empty string trivially
    "contains no forbidden words".
  * Each task runs best-of-N with N configurable; a single run is not a trend.
  * Results are JSON so runs are diffable over time.
  * TIERS: "core" is the 23 original tasks (tasks.json); "hard" is 27 more
    (tasks-hard.json, produced by gen-hard-tasks.py).  The core tier ceilinged:
    the strongest model scored 23/23, so a candidate could only tie, and the
    suite could detect a regression but never a gain.
  * --baseline compares PERCENTAGES, not raw scores, and lists which individual
    tasks flipped.  Raw-score diffing across suites of different size is actively
    misleading: 23/23 -> 37/50 prints as "+14" while per-task accuracy has in
    fact fallen from 100% to 74%.
  * ADOPTION IS A FAILURE-SET COMPARISON, not a score comparison. A candidate is
    adopted when it fails nothing the incumbent passes; a one-point total gap on
    this suite is usually one coin-flip task. --gate splits the suite on that
    asymmetry: only tasks the baseline PASSED can disqualify, only tasks it
    FAILED can improve the verdict.
  * A PARTIAL RUN IS LABELLED AS ONE. --gate/--only/--tier/--category all write
    their selection into the results file with a complete_suite flag, so a
    12-task gate can never be read back as "12/50".
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENDPOINT = os.environ.get(
    "MODEL_EVAL_ENDPOINT", "http://127.0.0.1:10000/v1/chat/completions"
)


def discover_models(endpoint):
    """Ask the server what it serves.

    The model list used to be hardcoded, which made the harness unusable by
    anyone else and silently stale whenever a model was renamed.
    """
    base = endpoint.split("/v1/")[0] + "/v1/models"
    try:
        with urllib.request.urlopen(base, timeout=10) as r:
            return [m["id"] for m in json.load(r).get("data", [])]
    except Exception as e:
        sys.exit(
            f"could not list models from {base}: {e}\npass --models explicitly, or check --endpoint"
        )


# ----------------------------------------------------------------- graders
def g_contains_all(out, t):
    low = out.lower()
    if any(r.lower() in low for r in t.get("reject", [])):
        return False, "matched a reject string"
    miss = [e for e in t["expect"] if e.lower() not in low]
    return (not miss), ("missing " + ", ".join(miss) if miss else "ok")


def g_regex(out, t):
    for r in t.get("reject", []):
        if re.search(r, out, re.I):
            return False, f"matched reject /{r}/"
    for e in t["expect"]:
        if not re.search(e, out, re.I):
            return False, f"no match for /{e}/"
    return True, "ok"


def g_starts_with_any(out, t):
    head = re.sub(r"^[^a-z]*", "", out.strip().lower())[:40]
    ok = any(head.startswith(e.lower()) for e in t["expect"])
    return ok, "ok" if ok else f"starts with {head[:20]!r}"


def g_numeric(out, t):
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", out.replace(",", ""))]
    if not nums:
        return False, "no number in output"
    tol = t.get("tolerance", 0.01)
    ok = any(abs(n - e) <= tol for n in nums for e in t["expect"])
    return ok, "ok" if ok else f"got {nums[:4]} want {t['expect']}"


def g_exact_word(out, t):
    w = re.sub(r"[^a-z]", "", out.strip().lower())
    ok = w in [e.lower() for e in t["expect"]]
    return ok, "ok" if ok else f"got {out.strip()[:30]!r}"


def g_word_count(out, t):
    n = len(out.split())
    tol = t.get("tolerance", 0)
    ok = any(abs(n - e) <= tol for e in t["expect"])
    return ok, "ok" if ok else f"{n} words, want {t['expect']}"


def g_json_keys(out, t):
    s = re.sub(r"^```(?:json)?|```$", "", out.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return False, "no JSON object found"
    try:
        d = json.loads(m.group(0))
    except Exception as e:
        return False, f"invalid JSON: {e}"
    miss = [k for k in t["expect"] if k not in d]
    return (not miss), ("missing keys " + ",".join(miss) if miss else "ok")


def g_contains_any_and_short(out, t):
    low = out.lower()
    if not any(e.lower() in low for e in t["expect"]):
        return False, "no key term present"
    n = len(out.split())
    if n > t.get("max_words", 40):
        return False, f"too long ({n} words)"
    return True, "ok"


GRADERS = {
    "contains_all": g_contains_all,
    "regex": g_regex,
    "starts_with_any": g_starts_with_any,
    "numeric": g_numeric,
    "exact_word": g_exact_word,
    "word_count": g_word_count,
    "json_keys": g_json_keys,
    "contains_any_and_short": g_contains_any_and_short,
}


# ----------------------------------------------------------------- runner
def ask(endpoint, model, prompt, system, max_tokens, timeout=900, sampling=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    # Sampling was hardcoded to temperature=0 in an earlier version, which made the
    # harness STRUCTURALLY UNABLE to measure any model that is loop-prone under greedy
    # decoding.  One candidate scored 44/50 purely because temperature 0 made it emit
    # 14,000-17,000 characters of reasoning and then an empty response on six tasks it
    # answers in one line at its own recommended sampling, where it scored 50/50.  That
    # was reported as a capability gap.  It was a measurement artefact.
    # The default stays temperature 0 so old baselines remain comparable; pass
    # --temperature to test a model at the sampling it is actually meant to run at.
    body = {"model": model, "messages": msgs, "max_tokens": max_tokens, "temperature": 0}
    if sampling:
        body.update(sampling)
    body = json.dumps(body).encode()
    req = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
    except Exception as e:
        return {"error": str(e), "content": "", "secs": time.time() - t0}
    ch = d["choices"][0]
    tm = d.get("timings") or {}
    return {
        "content": (ch["message"].get("content") or "").strip(),
        "reasoning": (ch["message"].get("reasoning_content") or "").strip(),
        "finish": ch.get("finish_reason"),
        "secs": time.time() - t0,
        "tok_s": tm.get("predicted_per_second"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"chat-completions URL (default {DEFAULT_ENDPOINT})",
    )
    ap.add_argument("--models")
    ap.add_argument("--category")
    ap.add_argument("--tier", choices=["core", "hard", "all"], default="all")
    ap.add_argument("--best-of", type=int, default=1)
    # Sampling overrides.  Needed for a FAIR cross-model comparison: models come with
    # different recommended presets, and forcing one preset on all of them measures how
    # well each tolerates that preset, not how capable it is.
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--top-p", type=float)
    ap.add_argument("--top-k", type=int)
    ap.add_argument("--min-p", type=float)
    ap.add_argument("--presence-penalty", type=float)
    ap.add_argument(
        "--max-tokens",
        type=int,
        default=16000,
        help="reasoning burns thousands of characters before the answer; on "
        "this machine 300, 500, 2000 and 4500 each produced EMPTY content "
        "that was read as a capability failure",
    )
    # chat_template_kwargs passthrough (llama.cpp accepts it in the request body).  Needed
    # for models whose template defaults to thinking on: with it on, a small token budget
    # yields reasoning and empty content on every task, so the suite measures the budget.
    #   --chat-kwargs '{"enable_thinking": false}'
    ap.add_argument("--chat-kwargs")
    # Concurrency.  DEFAULT STAYS 1.  Batching changes GEMM shapes and reduction order, so
    # concurrent decoding is not guaranteed bit-identical to sequential even at temperature
    # 0 -- and any baseline recorded sequentially was recorded at --jobs 1.  Raise it only
    # for exploratory runs, or after proving identity on your own hardware.
    ap.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="concurrent requests (1 = sequential, matches sequential baselines)",
    )
    ap.add_argument("--baseline")
    ap.add_argument("--no-system", action="store_true")
    ap.add_argument(
        "--out", default=None, help="results JSON (default ./model-eval-<timestamp>.json)"
    )
    # ---- failure-set gate ------------------------------------------------------------
    ap.add_argument("--only", metavar="IDS", help="run only these task ids (comma list)")
    ap.add_argument(
        "--gate",
        choices=["passed", "failed", "all"],
        default="all",
        help="restrict to tasks the --baseline model PASSED (the only ones that "
        "can disqualify a candidate) or FAILED (upside only). "
        "Requires --baseline.",
    )
    ap.add_argument(
        "--gate-model",
        metavar="NAME",
        help="which model key inside --baseline to gate against "
        "(default: the sole key; error if ambiguous)",
    )
    ap.add_argument(
        "--gate-stop-after",
        type=int,
        default=0,
        metavar="N",
        help="abort after N tasks that the baseline passed have FAILED "
        "(0 = off).  Each is retried once before it counts.",
    )
    ap.add_argument(
        "--order",
        choices=["file", "baseline-slowest", "baseline-fastest"],
        default="file",
        help="task order.  baseline-slowest puts the baseline's most expensive "
        "tasks first, so a doomed candidate reveals itself in minutes.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected task ids in run order and exit, so the "
        "selection can be checked without taking the GPU",
    )
    a = ap.parse_args()

    # tasks.json predates tiering, so anything without an explicit tier is core.
    tasks = json.load(open(os.path.join(HERE, "tasks.json")))["tasks"]
    for t in tasks:
        t.setdefault("tier", "core")
    hard_path = os.path.join(HERE, "tasks-hard.json")
    if os.path.exists(hard_path):
        tasks += json.load(open(hard_path))["tasks"]
    if a.tier != "all":
        tasks = [t for t in tasks if t.get("tier", "core") == a.tier]
    if a.category:
        tasks = [t for t in tasks if t["category"] == a.category]
    if not tasks:
        sys.exit(f"no tasks matched tier={a.tier} category={a.category}")

    # ---- failure-set gate: selection and ordering -------------------------------------
    base_rows = {}
    gating = a.gate != "all" or a.gate_stop_after or a.order != "file"
    if a.baseline:
        _b = json.load(open(a.baseline))["results"]
        if a.gate_model:
            if a.gate_model not in _b:
                sys.exit(
                    f"--gate-model {a.gate_model!r} not in {a.baseline}; it holds: "
                    + ", ".join(repr(k) for k in _b)
                )
            _bm = a.gate_model
        elif len(_b) == 1:
            _bm = next(iter(_b))
        elif gating:
            # Ambiguous, and the gate would silently pick one.  Multi-model baselines are
            # fine for the percentage comparison at the end; they are not fine here.
            sys.exit(
                f"{a.baseline} holds {len(_b)} models -- name one with --gate-model: "
                + ", ".join(repr(k) for k in _b)
            )
        else:
            _bm = None
        if _bm is not None:
            base_rows = {r["id"]: r for r in _b[_bm]["rows"]}
            print(f"gate baseline: {_bm} -- {_b[_bm]['score']}/{_b[_bm]['total']} ({a.baseline})")
    elif gating:
        sys.exit("--gate / --gate-stop-after / --order require --baseline FILE.json")

    # A guard that cannot fire is worse than no guard.  With more than one worker every
    # task is dispatched before the first result is read, so the abort could only trigger
    # after the GPU time it exists to save.  Refuse the combination rather than accept it
    # and silently do nothing.
    if a.gate_stop_after and a.jobs > 1:
        sys.exit(
            "--gate-stop-after needs --jobs 1: with concurrency every task is already "
            "computed before the first result is read, so the abort saves nothing."
        )

    if a.only:
        want = {i.strip() for i in a.only.split(",") if i.strip()}
        missing = want - {t["id"] for t in tasks}
        if missing:  # a typo would otherwise silently shrink the run -- same class of trap
            sys.exit(f"--only: no such task id(s): {', '.join(sorted(missing))}")
        tasks = [t for t in tasks if t["id"] in want]

    if a.gate != "all":
        want_pass = a.gate == "passed"
        # A task absent from the baseline is neither passed nor failed there.  Dropping it
        # silently would hide genuinely new coverage, so say so instead.
        absent = [t["id"] for t in tasks if t["id"] not in base_rows]
        if absent:
            print(
                f"warning: {len(absent)} task(s) not in the baseline, excluded from "
                f"--gate {a.gate}: {', '.join(absent)}"
            )
        tasks = [t for t in tasks if base_rows.get(t["id"], {}).get("pass") == want_pass]
        if not tasks:
            sys.exit(f"no tasks matched --gate {a.gate}")

    if a.order != "file":
        rev = a.order == "baseline-slowest"
        tasks.sort(key=lambda t: base_rows.get(t["id"], {}).get("secs") or 0, reverse=rev)

    if a.dry_run:
        print(f"\ndry-run -- {len(tasks)} task(s), in run order:")
        for t in tasks:
            br = base_rows.get(t["id"], {})
            print(
                f"  {t['id']:<20} {t['category']:<13} baseline "
                f"{'pass' if br.get('pass') else 'FAIL' if br else '--':<4} "
                f"{(str(br.get('secs')) + 's') if br.get('secs') is not None else ''}"
            )
        est = sum((base_rows.get(t["id"], {}).get("secs") or 0) for t in tasks)
        print(
            f"\nbaseline wall time for this selection: {est / 60:.1f} min "
            f"(the candidate will differ with its own decode rate)"
        )
        return

    served = discover_models(a.endpoint)
    # Model names frequently CONTAIN commas ("06. Qwen3.6-27B (coder, UD-Q5_K_XL)"), so a
    # naive split(",") tears one name into two nonexistent ones and every task 404s with a
    # perfect 0/50 that looks like catastrophic model failure.  That happened.  Take the
    # string whole if it names a real model; only fall back to comma-splitting for lists.
    if a.models:
        known = set(served)
        if a.models.strip() in known:
            models = [a.models.strip()]
        else:
            parts = [m.strip() for m in a.models.split(",")]
            models = parts if all(p in known for p in parts) else [a.models.strip()]
    else:
        models = served
    if not models:
        sys.exit("no models to test")

    system = (
        None
        if a.no_system
        else (
            "Default to flowing prose. Use bullet points, numbered lists, or headers only when "
            "the content is genuinely enumerable. Follow output-format instructions exactly."
        )
    )

    tier_counts = {}
    for t in tasks:
        tier_counts[t.get("tier", "core")] = tier_counts.get(t.get("tier", "core"), 0) + 1
    sampling = {}
    for flag, key in (
        ("temperature", "temperature"),
        ("top_p", "top_p"),
        ("top_k", "top_k"),
        ("min_p", "min_p"),
        ("presence_penalty", "presence_penalty"),
    ):
        v = getattr(a, flag)
        if v is not None:
            sampling[key] = v
    if a.chat_kwargs:
        sampling["chat_template_kwargs"] = json.loads(a.chat_kwargs)

    print(f"model-eval -- {len(tasks)} tasks x {len(models)} models, best-of-{a.best_of}")
    print(f"endpoint: {a.endpoint}")
    print(f"tiers: {tier_counts}")
    print(f"sampling: {sampling if sampling else 'temperature=0 (default, greedy)'}")
    print(f"system prompt: {'none' if a.no_system else 'prose-default'}\n")

    results = {}
    for m in models:
        per_cat, per_tier, rows, errs = {}, {}, [], 0
        print(f"=== {m} ===")

        def _run_task(t):
            """One task, best-of retries included.  Pure with respect to shared state so
            it is safe to run concurrently; grading is CPU-only and the result is
            returned rather than appended, so ordering is restored by the caller."""
            passed, why, best = False, "", None
            for _ in range(a.best_of):
                r = ask(a.endpoint, m, t["prompt"], system, a.max_tokens, sampling=sampling)
                best = best or r
                if r.get("error"):
                    why = "API: " + r["error"][:60]
                    continue
                if not r["content"]:
                    # empty content is NEVER a pass and NEVER a content failure.  The
                    # finish reason and reasoning length are recorded because they are
                    # what distinguishes a starved budget from a model that said nothing.
                    why = f"EMPTY (finish={r['finish']}, reasoning={len(r.get('reasoning', ''))}c)"
                    continue
                ok, w = GRADERS[t["grader"]](r["content"], t)
                best = r
                if ok:
                    passed, why = True, w
                    break
                why = w
            return passed, why, best

        if a.jobs > 1:
            # Collected by task index and replayed in the original order below, so the
            # transcript and the row order match a sequential run exactly.
            with ThreadPoolExecutor(max_workers=a.jobs) as ex:
                computed = list(ex.map(_run_task, tasks))
        else:
            computed = None

        aborted, new_fails = None, []
        for _i, t in enumerate(tasks):
            passed, why, best = computed[_i] if computed is not None else _run_task(t)
            # Only a task the BASELINE PASSED can disqualify.  Retry it once before
            # believing it: an empty response from runaway reasoning and a transient API
            # error both present as a failure, and both have faked a regression here.
            if base_rows.get(t["id"], {}).get("pass") and not passed:
                print(f"  ....  {t['id']:<18} new failure ({why[:40]}) -- confirming")
                passed, why, best = _run_task(t)
                if not passed:
                    new_fails.append(t["id"])
            if why.startswith("EMPTY") or why.startswith("API:"):
                errs += 1
                mark = "ERR "
            else:
                mark = "PASS" if passed else "FAIL"
            per_cat.setdefault(t["category"], []).append(passed)
            per_tier.setdefault(t.get("tier", "core"), []).append(passed)
            rows.append(
                {
                    "id": t["id"],
                    "cat": t["category"],
                    "tier": t.get("tier", "core"),
                    "pass": passed,
                    "why": why,
                    "secs": round(best["secs"], 1) if best else None,
                    "output": (best or {}).get("content", "")[:200],
                }
            )
            print(f"  {mark}  {t['id']:<18} {t['category']:<13} {why[:52]}")
            if a.gate_stop_after and len(new_fails) >= a.gate_stop_after:
                aborted = (
                    f"{len(new_fails)} confirmed new failure(s) vs baseline "
                    f"({', '.join(new_fails)}) after {_i + 1}/{len(tasks)} tasks"
                )
                print(f"\n  ABORT -- {aborted}")
                print(
                    f"     Dominance is impossible; the remaining {len(tasks) - _i - 1} "
                    f"task(s) cannot change that.  Stopping to free the GPU."
                )
                break
        score = sum(r["pass"] for r in rows)
        cats = {c: f"{sum(v)}/{len(v)}" for c, v in per_cat.items()}
        tiers = {k: f"{sum(v)}/{len(v)}" for k, v in per_tier.items()}
        print(f"  ----> {score}/{len(rows)}  ({100 * score / len(rows):.0f}%)   errors={errs}")
        print(f"        by tier: {tiers}")
        print(f"        by cat:  {cats}\n")
        results[m] = {
            "score": score,
            "total": len(rows),
            "errors": errs,
            "by_category": cats,
            "by_tier": tiers,
            "rows": rows,
        }
        if base_rows:
            # The verdict this suite is actually for.  Stated even on a complete run,
            # because "49/50" and "fails nothing the incumbent passes" are different
            # claims.  A recovered task is a claim about the BASELINE row -- re-run it
            # against the baseline model in the same sitting before quoting it.
            results[m]["new_failures"] = new_fails
            results[m]["recovered"] = sorted(
                r["id"]
                for r in rows
                if r["pass"] and base_rows.get(r["id"], {}).get("pass") is False
            )
        if aborted:
            results[m]["aborted"] = aborted
            print(
                f"  PARTIAL RUN -- {score}/{len(rows)} of a {len(tasks)}-task selection; "
                f"this is NOT a suite score."
            )

    print("=" * 74)
    print(f"{'model':<48}{'score':>10}{'errors':>9}")
    print("=" * 74)
    for m, r in sorted(results.items(), key=lambda x: -x[1]["score"]):
        print(f"{m:<48}{r['score']:>4}/{r['total']:<5}{r['errors']:>9}")

    out = a.out or f"model-eval-{time.strftime('%Y%m%d-%H%M%S')}.json"
    # Record HOW the run was made.  Two baselines on this machine do not say what sampling
    # or token budget produced them, which makes "match the baseline's settings" an
    # instruction nobody can check -- the numbers have to be reasoned about instead of read.
    json.dump(
        {
            "when": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system": system,
            "endpoint": a.endpoint,
            "settings": {
                "sampling": sampling or {"temperature": 0},
                "max_tokens": a.max_tokens,
                "jobs": a.jobs,
                "best_of": a.best_of,
                "chat_kwargs": a.chat_kwargs,
            },
            "selection": {
                "tier": a.tier,
                "category": a.category,
                "only": a.only,
                "gate": a.gate,
                "order": a.order,
                "baseline": a.baseline,
                "n_tasks": len(tasks),
                "complete_suite": (
                    a.gate == "all" and not a.only and a.tier == "all" and not a.category
                ),
            },
            "results": results,
        },
        open(out, "w"),
        indent=1,
    )
    print(f"\nsaved -> {out}")

    if a.baseline:
        base = json.load(open(a.baseline))["results"]
        print("\n=== vs baseline ===")
        for m, r in results.items():
            if m not in base:
                print(f"  {m:<48} (not in baseline)")
                continue
            b = base[m]
            # Compare PERCENTAGES, never raw scores.  The suite grew from 23 to 50 tasks,
            # so a raw diff against an older baseline reads 23 -> 37 as "+14", a big win,
            # when per-task accuracy has actually dropped from 100% to 74%.
            bp = 100 * b["score"] / b["total"]
            rp = 100 * r["score"] / r["total"]
            d = rp - bp
            if b["total"] != r["total"]:
                note = f"  [SUITE CHANGED {b['total']}->{r['total']} tasks; compare pp, not score]"
            elif d < 0:
                note = "  <-- REGRESSION"
            else:
                note = ""
            print(
                f"  {m:<44} {b['score']}/{b['total']} ({bp:.0f}%) -> "
                f"{r['score']}/{r['total']} ({rp:.0f}%)  {d:+.0f} pp{note}"
            )
            # Per-task flips are what actually matters for a regression gate, and they stay
            # meaningful even when the suite size changed: only shared task ids are compared.
            was = {row["id"]: row["pass"] for row in b["rows"]}
            now = {row["id"]: row["pass"] for row in r["rows"]}
            broke = sorted(i for i in was.keys() & now.keys() if was[i] and not now[i])
            fixed = sorted(i for i in was.keys() & now.keys() if now[i] and not was[i])
            added = sorted(now.keys() - was.keys())
            if broke:
                print(f"      pass -> FAIL: {', '.join(broke)}")
            if fixed:
                print(f"      fail -> pass: {', '.join(fixed)}")
            if added:
                new_pass = sum(now[i] for i in added)
                print(f"      new tasks not in baseline: {len(added)} ({new_pass} passed)")


if __name__ == "__main__":
    main()
