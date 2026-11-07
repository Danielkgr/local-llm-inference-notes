# A deterministic benchmark and its task ceiling

The evaluation suite used deterministic graders and detected useful
regressions.  Its task selection was less successful.  The original 23-task
suite reached a perfect score, and the expanded 50-task suite did so again in
its first reference run.  It could detect some regressions but could not
measure further improvement above that ceiling.

## Why no LLM judge

I used fixed graders to keep the scoring independent of another model's
preferences, version, and sampling.  This limits the tasks to questions those
graders can decide.  It does not make the suite a complete measure of quality.

So every task in the suite is graded by a deterministic function: substring
match, regex, numeric comparison with a tolerance, exact word, word count, or
JSON key presence.  Tasks are written so short answers are the only correct
answers, which is what makes deterministic grading possible.

Three rules fell out of running it:

**Empty content is an error, not a failure.**  Reasoning models spend their
token budget on `reasoning_content` before emitting anything.  At a 420-token
cap, three different models returned `content=''` with
`finish_reason='length'`.  An empty string trivially satisfies "contains none
of the forbidden words", so scoring it as a pass is wrong, and scoring it as a
content failure blames the model for the harness's cap.  It is counted
separately.

**Compare percentages, never raw scores.**  The suite grew from 23 tasks to 50.
A raw diff against an older baseline reads 23 to 37 as "+14", which looks like
a large gain, while per-task accuracy has in fact fallen from 100 per cent to
74 per cent.

**Report which individual tasks flipped.**  A score that moves by one point
tells you nothing about whether the same task broke or a different one did.
Only task ids shared between the two runs are compared, so the flip list stays
meaningful even when the suite size changed.

## The ceiling, twice

The 23-task core suite discriminated usefully at first.  On 31 July the field
ranged from 18/23 to 22/23.  One day later, after a system-prompt fix, two
models scored 23/23.  At that point the suite could still detect a regression,
but a candidate could only ever tie, so it could not measure a gain.

A 27-task hard tier was generated to restore headroom.  Its stated design
target, written into the generator, was roughly 70 to 80 per cent for the
reference model on the merged 50-task suite.

The reference model scored **50/50**.

| run | suite | result |
|---|---|---|
| 31 Jul | core 23 | best 22/23, field 18 to 22 |
| 1 Aug | core 23 | two models at 23/23, ceiling reached |
| 1 Aug | merged 50 | reference model 50/50, target was 35 to 40 |

Across every healthy run on the merged suite since, the whole field sits
between 44/50 and 50/50, a band of 88 to 100 per cent.  The hard tier made the
suite longer and slightly more discriminating between weaker candidates.  It
did not put headroom back above the strongest one, which was the entire reason
it was written.

## Why the calibration failed

The hard tasks were written by someone who already knew what the reference
model found difficult, and were then checked against that same model.  Tasks it
failed were the ones that felt hard, so the set converged on tasks it could
nearly all do.  That is a possible explanation for the poor calibration.  The
scores establish the ceiling, not the full cause of how the tasks were
selected.

A further task set could use tasks drawn from real failures observed in use, or
held out entirely and never checked against the reference until the day they
are scored.  That has not been done here, so the ceiling stands.

## Scope

The suite remains useful for known regressions, but its ceiling limits model
ranking.  Passing every task does not establish broad capability or
equivalence.  The portable tool and its scope are described in the [tools
documentation](../tools/README.md).
