# Measurement rules

Current procedure, reviewed 7 November 2026.  Notes 01 to 16 preserve earlier
experiments and their original protocols.  Their fixed noise bands, compulsory
same-session controls, and early-exit adoption gate are historical.  The
current procedure below supersedes those instructions for Box and Strix.

## Authority and scope

Read the host's `/data/maintenance/RETEST-RULES.md` and
`/data/maintenance/TEST-ACCEPTANCE-POLICY.json` before planning a test.
Sections 8, 9, and 15 define the complete compact suite, global hold, and
acceptance policy.  Later sections record individual grants.  The two hosts
have different grant histories, so the files are not interchangeable.

The global model-test hold remains installed on both hosts.  Reviewing this
repository, preparing code, or passing CPU tests does not authorise inference,
benchmarking, conversion, a maintenance window, or promotion.  A dated
exception covers only its named host, job, controller, and time.  Ordinary
serving continues.

Before authorised model work, run `python3 /data/apps/model-test-hold.py check`
and use `/data/apps/model-test-run.sh -- ...` with the host's coordination
wrapper.  Box windows also use `/data/apps/ab-maintenance-lock.sh run --force
-- ...`.  Here `--force` removes idle waiting.  It cannot bypass the hold.  The
generic GPU helper in this repository does not replace either wrapper.

Documents trees and their associated session content are excluded from host
reviews.  Keep discovery inside allowed directories, do not follow links into
excluded trees, and do not inspect session stores without first establishing an
allowed project association from minimal metadata.

## Design the comparison before loading anything

**Freeze the question and workload.**  Record model and runtime identity,
precision, context per slot, concurrency, input and output budgets, sampling,
template, cache state, and hardware placement.  A model alias is not weight
identity.  A service description is not its effective command line.

**Reuse applicable evidence.**  A different date or operator does not require
another incumbent load.  Bind the reference to its source and hash, and check
the workload and configuration match.  Record meaningful differences.  A
changed driver, topology, precision, template, or measurement definition can
invalidate a comparison.  Explain that mismatch before replacing the reference.
The stale-baseline error in [note
05](notes/05-the-control-that-killed-a-false-claim.md) still matters, but an
automatic reference rerun is no longer the remedy.

**Screen changes before building.**  A newer runtime that does not touch the
code behind a known failure does not earn another outage.  Prepare builds,
downloads, fixtures, manifests, rollback, and the downtime estimate outside the
maintenance lock.  Routine suites belong overnight unless separately
authorised.

## Acceptance has units

The current policy is `metric-aware-20261028-v1`.  Use the shared CPU evaluator
at `/data/apps/lane-gate/acceptance.py` for host performance comparisons, and
record the policy SHA256 with the measurements.  The reviewed policy hash is in
the [evidence snapshot](evidence/2026-11-07-review.json).

| Metric | Accepted degradation from a matched reference |
|---|---|
| Fresh or returning prompt-processing duration, seconds | At most `max(0.05 * reference, 0.5)` seconds slower |
| Decode or prefill rate, tokens per second | At least `0.95 * reference` |
| TTFT, tool round trip, retrieval, audio, or image latency | Its own declared metric rule, generally 5%, with no universal 0.5-second allowance |
| Loading time | Report cold or warm state.  Observe unless an explicit contract makes it a gate. |
| Correctness, safety coverage, retrieval facts, precision, identity, or recovery | The exact declared requirement.  Timing allowances do not apply. |

These are engineering acceptance tolerances.  They are not measured noise
distributions or significance tests.  Optional absolute jitter must come from
matched reference evidence frozen before the candidate, with source hashes.
Candidate variability cannot widen its own acceptance band.

Preserve unrounded values and the declared aggregation.  Four returning turns
may use an upper median.  They are different requests, not four independent
repetitions of one request.  Do not gate equivalent prefill time and rate
twice.

Missing, zero, or nonfinite measurements are incomplete.  Known workload or
configuration mismatches are not comparable.  Neither establishes a regression,
and neither can qualify a candidate.  Deadlines bound execution.  Exceeding one
does not prove bad model quality or that a model cannot fit.

## Complete the suite with one candidate load

Keep the candidate loaded for control checks, coding and performance telemetry,
streamed tools, all 15 required safety repetitions, and relevant retrieval.
Collect speed during useful work.  Do not add a baseline arm, automatic draft
tuning, repeated warm-up, or a separate speed-only stage by default.

Continue after speed, coding, and safety failures, and report every planned
check.  Those failures still prevent adoption.  User STOP or a fatal engine or
resource failure requires safe cleanup and explicit incomplete results for
unfinished checks.  Do not score requests sent to a dead server as model
answers.

Near-limit retrieval uses `/data/apps/lane-gate/needle-batch.py`.  One frozen
prompt contains separately keyed facts at 10%, 50%, and 90%.  Check all three
in one final answer.  Record protocol, prompt hash, actual token count, and one
request.  This is one joint test, not three independent trials.  A missing or
budget-exhausted final answer cannot pass.  Run it when the change affects the
attention, context, or KV path, as the host rules require.

## Trust the apparatus

Inspect loaded libraries when backend identity matters.  Check both sides of a
comparison rather than trusting launcher names.  Greedy text identity is useful
only under a controlled execution path.  Different kernels, batching, or
precision can change rounding and therefore tokens.  Greedy decoding removes
sampling randomness, not every possible cause of failure.

Use deterministic graders for the tasks they can actually decide.  A perfect
score may show a ceiling.  An exact zero across unrelated tasks may show a
shared transport failure.  Preserve task-level failures and errors so those
possibilities remain distinguishable.

Record capped output, empty content, finish reason, and reasoning length.
Inspect the apparatus before interpreting either as a capability result.  Keep
the token budget and resolved sampling in the result itself.  Preserve failed
attempts and waivers rather than overwriting them with a later pass.

The portable `model-eval` tool reports a limited deterministic suite.  Its
optional historical early-exit gate remains available for other environments.
It is not the complete host qualification runner and must not be used to
short-circuit the Box or Strix procedure.  A suite score is not adoption
authority.

## Adoption and recovery are separate claims

Keep measurement completion, qualification, a human waiver, deployment, and
restoration as separate states.  A waiver names the exact failed gate and
scope.  It does not change the raw result, relax every future run, or turn the
remaining failures into passes.

Verify the actual client and routed service after a change, alongside binary
identity, kernel and engine logs, owned-worker cleanup, and resident/admission
restoration.  Keep rollback material and verify backup selection.  A passing
backup plan does not prove a fresh archive exists or has been restored.

Use the owned STOP mechanism.  Never kill a lock supervisor or strand admission
closed.  A previously authorised promotion does not authorise this review to
change serving configuration.

See [note 17](notes/17-complete-tests-without-duplicate-work.md) for the
procedure change, [CURRENT.md](CURRENT.md) for the observed setup, and the
[review](reviews/2026-11-07.md) for evidence boundaries and remaining gaps.
