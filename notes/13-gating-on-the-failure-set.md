# A historical adoption gate based on failure sets

The earlier adoption gate compared task failures rather than total scores.  It
ran the tasks the incumbent had passed first and could stop after confirmed new
failures.  On its first use, a reported recovery exposed a bad baseline row.

This is a historical procedure.  Since 27 October 2026, Box and Strix require
the complete planned suite after a quality or speed miss.  See
[METHOD.md](../METHOD.md) for the current procedure.

## Why not compare totals

[Note 12](12-four-sampling-profiles-three-rankings.md) settled this on the same
suite: across twelve runs of one model, seven of fifty tasks flipped at least
once, and a three-point gap in one sitting evaporated over three.  A one- or
two-point difference between two models is, on this suite, usually one
coin-flip task.

The historical gate used this criterion: **the candidate fails nothing the
incumbent passes.**  That is a statement about sets, it is robust to a task or
two of noise in the tasks both models fail, and it is what adoption actually
requires.

Restating the decision that way splits the suite in two, and the halves are not
symmetric:

| Tasks the baseline | Can disqualify? | Can improve the verdict? |
|---|---|---|
| **passed** | yes | no |
| **failed** | no | yes |

The gate placed expensive disqualifying tasks first.

## The gate

Stage one runs only the tasks the incumbent passed.  Within that stage, tasks
are ordered by the incumbent's own recorded wall time, slowest first, on the
reasoning that the tasks which cost the most are also the ones a weaker
candidate is most likely to fail.  After a configurable number of confirmed new
failures the run aborts and says so: dominance is already impossible, and the
remaining tasks cannot change that.

Stage two runs only the tasks the incumbent failed.  It cannot disqualify
anything, so it runs afterwards, and its result is upside.

Three details in the implementation earned their place:

**Every new failure is retried once before it counts.**  On this suite an empty
response after runaway reasoning and a transient API error both present as a
failure, and both have faked a regression here before.  A retry costs one task;
a false abort costs the whole evaluation.

**Early abort refuses to run concurrently.**  With more than one worker, every
task is dispatched before the first result is read, so the abort could only
fire after the GPU time it exists to save.  The harness rejects the combination
rather than accepting it and quietly doing nothing.  The requested combination
could not save work through early abort.

**The harness labels a partial run as partial.**  The results file records
which selection produced it: tier, category, explicit task list, gate mode,
baseline, and a boolean saying whether this was the complete suite.  A
twelve-task gate must never be readable later as "12/50".  In the same spirit,
an unknown task id is a hard error rather than a silently smaller run, and
tasks absent from the baseline are reported rather than dropped, since they are
neither passed nor failed there and excluding them silently would hide new
coverage.

## First real use: two candidates, one confounded recovery

| candidate | stage 1 (baseline passed) | stage 2 (baseline failed) | new failures | verdict |
|---|---|---|---|---|
| smaller quantisation of the incumbent | 49/49 | 0/1 | none | dominates |
| different model, same class | 47/47 | 1/3 | none | dominates |

Both cleared stage one completely.  The second recovered a long-context task
the incumbent had failed, which reads as a straightforward gain.

**It was not.**  Re-running that single task against the incumbent produced an
empty response: finish reason `length`, 29,734 characters of reasoning content,
102 seconds, no answer.  The baseline row that made this a "recovery" was a
token budget running out, not a capability the incumbent lacks.

That check cost one task and one minute.  Without it, the write-up would have
claimed a capability difference on the strength of a row in a file, and the row
was the same starvation artefact that has now produced a false negative on this
machine repeatedly, at 300 tokens, at 500, and at 4,500.

So the rule the gate needed, and did not originally have: **a recovered task is
a claim about the baseline, and the baseline is a file, not a measurement.**
At the time, a same-session control exposed the error.  The current
[METHOD](../METHOD.md) instead requires applicable, provenance-bound references
and does not automatically reload an unchanged incumbent.

A third candidate, gated on a different machine, recorded content failures: 44
out of 50 with five new failures against two recoveries, verdict `REGRESSES`,
incumbent restored automatically by the harness.  The same run recorded its
VRAM and shared-memory deltas against the incumbent and its decode rate across
three samples, because a model that scores the same while costing more memory
is not a neutral swap.

## Scope

This gate is retained as a historical design and a portable tool option.  Since
27 October 2026, Box and Strix require the complete planned suite even after a
failed gate.  They reuse applicable references and report errors as incomplete
work.  See [METHOD.md](../METHOD.md) and [note
17](17-complete-tests-without-duplicate-work.md).
