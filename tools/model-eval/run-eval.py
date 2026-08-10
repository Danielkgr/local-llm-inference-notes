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
"""
import argparse, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENDPOINT = os.environ.get(
    "MODEL_EVAL_ENDPOINT", "http://127.0.0.1:10000/v1/chat/completions")


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
        sys.exit(f"could not list models from {base}: {e}\n"
                 f"pass --models explicitly, or check --endpoint")


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
    head = re.sub(r'^[^a-z]*', '', out.strip().lower())[:40]
    ok = any(head.startswith(e.lower()) for e in t["expect"])
    return ok, "ok" if ok else f"starts with {head[:20]!r}"


def g_numeric(out, t):
    nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', out.replace(',', ''))]
    if not nums:
        return False, "no number in output"
    tol = t.get("tolerance", 0.01)
    ok = any(abs(n - e) <= tol for n in nums for e in t["expect"])
    return ok, "ok" if ok else f"got {nums[:4]} want {t['expect']}"


def g_exact_word(out, t):
    w = re.sub(r'[^a-z]', '', out.strip().lower())
    ok = w in [e.lower() for e in t["expect"]]
    return ok, "ok" if ok else f"got {out.strip()[:30]!r}"


def g_word_count(out, t):
    n = len(out.split())
    tol = t.get("tolerance", 0)
    ok = any(abs(n - e) <= tol for e in t["expect"])
    return ok, "ok" if ok else f"{n} words, want {t['expect']}"


def g_json_keys(out, t):
    s = re.sub(r'^```(?:json)?|```$', '', out.strip(), flags=re.M).strip()
    m = re.search(r'\{.*\}', s, re.S)
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
    "contains_all": g_contains_all, "regex": g_regex, "starts_with_any": g_starts_with_any,
    "numeric": g_numeric, "exact_word": g_exact_word, "word_count": g_word_count,
    "json_keys": g_json_keys, "contains_any_and_short": g_contains_any_and_short,
}


# ----------------------------------------------------------------- runner
def ask(endpoint, model, prompt, system, max_tokens, timeout=900, sampling=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
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
    req = urllib.request.Request(endpoint, data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
    except Exception as e:
        return {"error": str(e), "content": "", "secs": time.time() - t0}
    ch = d["choices"][0]
    tm = d.get("timings") or {}
    return {"content": (ch["message"].get("content") or "").strip(),
            "reasoning": (ch["message"].get("reasoning_content") or "").strip(),
            "finish": ch.get("finish_reason"), "secs": time.time() - t0,
            "tok_s": tm.get("predicted_per_second")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT,
                    help=f"chat-completions URL (default {DEFAULT_ENDPOINT})")
    ap.add_argument("--models"); ap.add_argument("--category")
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
    ap.add_argument("--max-tokens", type=int, default=4500,
                    help="reasoning burns thousands of characters; 2000 produced EMPTY "
                         "content on five tasks")
    ap.add_argument("--baseline"); ap.add_argument("--no-system", action="store_true")
    ap.add_argument("--out", default=None,
                    help="results JSON (default ./model-eval-<timestamp>.json)")
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

    system = None if a.no_system else (
        "Default to flowing prose. Use bullet points, numbered lists, or headers only when "
        "the content is genuinely enumerable. Follow output-format instructions exactly.")

    tier_counts = {}
    for t in tasks:
        tier_counts[t.get("tier", "core")] = tier_counts.get(t.get("tier", "core"), 0) + 1
    sampling = {}
    for flag, key in (("temperature", "temperature"), ("top_p", "top_p"), ("top_k", "top_k"),
                      ("min_p", "min_p"), ("presence_penalty", "presence_penalty")):
        v = getattr(a, flag)
        if v is not None:
            sampling[key] = v

    print(f"model-eval -- {len(tasks)} tasks x {len(models)} models, best-of-{a.best_of}")
    print(f"endpoint: {a.endpoint}")
    print(f"tiers: {tier_counts}")
    print(f"sampling: {sampling if sampling else 'temperature=0 (default, greedy)'}")
    print(f"system prompt: {'none' if a.no_system else 'prose-default'}\n")

    results = {}
    for m in models:
        per_cat, per_tier, rows, errs = {}, {}, [], 0
        print(f"=== {m} ===")
        for t in tasks:
            passed, why, best = False, "", None
            for _ in range(a.best_of):
                r = ask(a.endpoint, m, t["prompt"], system, a.max_tokens, sampling=sampling)
                best = best or r
                if r.get("error"):
                    why = "API: " + r["error"][:60]; continue
                if not r["content"]:
                    # empty content is NEVER a pass and NEVER a content failure
                    why = f"EMPTY (finish={r['finish']}, reasoning={len(r.get('reasoning',''))}c)"
                    continue
                ok, w = GRADERS[t["grader"]](r["content"], t)
                best = r
                if ok:
                    passed, why = True, w; break
                why = w
            if why.startswith("EMPTY") or why.startswith("API:"):
                errs += 1
                mark = "ERR "
            else:
                mark = "PASS" if passed else "FAIL"
            per_cat.setdefault(t["category"], []).append(passed)
            per_tier.setdefault(t.get("tier", "core"), []).append(passed)
            rows.append({"id": t["id"], "cat": t["category"], "tier": t.get("tier", "core"),
                         "pass": passed,
                         "why": why, "secs": round(best["secs"], 1) if best else None,
                         "output": (best or {}).get("content", "")[:200]})
            print(f"  {mark}  {t['id']:<18} {t['category']:<13} {why[:52]}")
        score = sum(r["pass"] for r in rows)
        cats = {c: f"{sum(v)}/{len(v)}" for c, v in per_cat.items()}
        tiers = {k: f"{sum(v)}/{len(v)}" for k, v in per_tier.items()}
        print(f"  ----> {score}/{len(rows)}  ({100*score/len(rows):.0f}%)   errors={errs}")
        print(f"        by tier: {tiers}")
        print(f"        by cat:  {cats}\n")
        results[m] = {"score": score, "total": len(rows), "errors": errs,
                      "by_category": cats, "by_tier": tiers, "rows": rows}

    print("=" * 74)
    print(f"{'model':<48}{'score':>10}{'errors':>9}")
    print("=" * 74)
    for m, r in sorted(results.items(), key=lambda x: -x[1]["score"]):
        print(f"{m:<48}{r['score']:>4}/{r['total']:<5}{r['errors']:>9}")

    out = a.out or f"model-eval-{time.strftime('%Y%m%d-%H%M%S')}.json"
    json.dump({"when": time.strftime("%Y-%m-%d %H:%M:%S"), "system": system,
               "endpoint": a.endpoint, "sampling": sampling or {"temperature": 0},
               "results": results}, open(out, "w"), indent=1)
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
            print(f"  {m:<44} {b['score']}/{b['total']} ({bp:.0f}%) -> "
                  f"{r['score']}/{r['total']} ({rp:.0f}%)  {d:+.0f} pp{note}")
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
