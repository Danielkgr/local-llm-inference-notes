# Shorter tests by removing duplicate work

On 27 October 2026, the testing procedure changed to reduce repeated work while
retaining the complete planned suite.  An applicable reference could be reused,
and one candidate load would cover coding, performance, tools, safety, and
required retrieval.  A failed quality or speed gate would no longer end the
run.

## The expensive part was repetition

The earlier approach treated a new session as a reason to measure the incumbent
again.  It could then add ordinary decoding, a draft comparison, a warm-up, a
speed stage, and separate long-context requests before completing quality work.
Each stage could repeat loading and admission downtime.

The replacement binds the adopted reference to its source and configuration.
Only a concrete mismatch makes that evidence inapplicable.  Candidate speed is
collected during coding and other useful work, with the same engine kept loaded
for tools, all 15 safety repetitions, and required retrieval.

The retrieval change is particularly easy to misdescribe.  One frozen prompt
contains three keyed facts at 10%, 50%, and 90%, and one final answer must
recover all three.  The record states the protocol, hash, actual token count,
and one request.  It is not three independent retrieval trials.

## Completeness survives a failure

A speed or correctness miss still blocks adoption, but the remaining planned
checks run.  A fatal engine failure or user STOP instead requires restoration
and explicit incomplete coverage.  Calling every later connection failure a bad
model answer would repeat [note 09](09-when-the-harness-scores-itself.md).

The 6 November Strix suite provides a concrete implementation record.  It ran
with one engine start and no reference reload, reported sixteen gate outcomes,
and restored the incumbent after about 944 seconds of downtime.  Its overall
result was FAIL.  Completing the suite did not erase that result.

This record demonstrates the compact execution shape.  It does not establish a
controlled before-and-after percentage reduction in downtime.

## Acceptance also changed

Fresh and returning seconds permit the greater of 5% or 0.5 seconds of
degradation.  Rates retain their percentage rule.  Correctness, retrieval,
precision, and recovery retain their own strict requirements.  These are
practical acceptance limits, not a newly measured statistical noise floor.

The complete current procedure is in [METHOD.md](../METHOD.md).  Source hashes
for the host rules, policy, shared runners, and the 6 November result are in
the [review evidence](../evidence/2026-11-07-review.json).
