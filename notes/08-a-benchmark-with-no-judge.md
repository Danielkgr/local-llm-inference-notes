# A benchmark with no LLM judge, and the ceiling it hit twice

**Question.**  Can you rank local models for your own work with a number rather
than a feeling, without using a model to grade models?

**Verdict.**  Yes for the grading.  Deterministic graders are cheap, unarguable,
and caught real regressions.  No for the difficulty calibration: the suite
ceilinged, the fix for the ceiling also ceilinged, and the second failure was
visible in the first run after it shipped.

## Why no LLM judge

A judge makes the measurement depend on the thing being measured.  If the judge
is the model under test, the result is circular.  If it is a different model,
every score now carries that model's biases, its version, and its sampling
settings, none of which are recorded in the number you end up quoting.

So every task in the suite is graded by a deterministic function: substring
match, regex, numeric comparison with a tolerance, exact word, word count, or
JSON key presence.  Tasks are written so short answers are the only correct
answers, which is what makes deterministic grading possible.

Three rules fell out of running it:

**Empty content is an error, not a failure.**  Reasoning models spend their token
budget on `reasoning_content` before emitting anything.  At a 420-token cap,
three different models returned `content=''` with `finish_reason='length'`.  An
empty string trivially satisfies "contains none of the forbidden words", so
scoring it as a pass is wrong, and scoring it as a content failure blames the
model for the harness's cap.  It is counted separately.

**Compare percentages, never raw scores.**  The suite grew from 23 tasks to 50.
A raw diff against an older baseline reads 23 to 37 as "+14", which looks like a
large gain, while per-task accuracy has in fact fallen from 100 per cent to 74
per cent.

**Report which individual tasks flipped.**  A score that moves by one point tells
you nothing about whether the same task broke or a different one did.  Only task
ids shared between the two runs are compared, so the flip list stays meaningful
even when the suite size changed.

## The ceiling, twice

The 23-task core suite discriminated usefully at first.  On 31 July the field
ranged from 18/23 to 22/23.  One day later, after a system-prompt fix, two models
scored 23/23.  At that point the suite could still detect a regression, but a
candidate could only ever tie, so it could not measure a gain.

A 27-task hard tier was generated to restore headroom.  Its stated design target,
written into the generator, was roughly 70 to 80 per cent for the reference model
on the merged 50-task suite.

The reference model scored **50/50**.

| run | suite | result |
|---|---|---|
| 31 Jul | core 23 | best 22/23, field 18 to 22 |
| 1 Aug | core 23 | two models at 23/23, ceiling reached |
| 1 Aug | merged 50 | reference model 50/50, target was 35 to 40 |

Across every healthy run on the merged suite since, the whole field sits between
44/50 and 50/50, a band of 88 to 100 per cent.  The hard tier made the suite
longer and slightly more discriminating between weaker candidates.  It did not
put headroom back above the strongest one, which was the entire reason it was
written.

## Why the calibration failed

The hard tasks were written by someone who already knew what the reference model
found difficult, and were then checked against that same model.  Tasks it failed
were the ones that felt hard, so the set converged on tasks it could nearly all
do.  Calibrating difficulty against a single reference is a fixed point, not a
measurement.

The honest fix is a difficulty source that does not come from the model under
test: tasks drawn from real failures observed in use, or held out entirely and
never checked against the reference until the day they are scored.  That has not
been done here, so the ceiling stands.

## What generalises

A benchmark has two independent jobs, and they fail independently.  Grading is
about whether a result is correct, and a deterministic grader settles that
cheaply and permanently.  Calibration is about whether the questions can
distinguish the candidates at all, and no amount of grading rigour fixes a set of
questions everyone passes.

The tell is a compressed score distribution.  When the field lands inside a few
points of the maximum, the suite has stopped measuring, whatever its pass rate
says.  Check the spread before trusting a comparison, and treat a perfect score
as a problem with the benchmark rather than a property of the model.
