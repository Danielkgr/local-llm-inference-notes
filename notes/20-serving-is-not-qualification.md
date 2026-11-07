# Strix deployment and later qualification

The abliterated Strix model went live before its full suite ran.  The later
suite, on 6 November 2026, failed several checks.  Only the safety score had a
waiver.  The controller restored the same deployed model after the run.

## A health-only cutover

The abliterated 35B-A3B model replaced stock weights on 3 November under an
explicit health-only cutover grant.  The runtime, context, and client route
stayed in place.  The safety score had a specific waiver, and the complete
compact suite was scheduled separately.

The suite ran on 6 November and reported FAIL.

| Area | Result |
|---|---|
| Inherited coding | Six of seven passed, `merge_ranges` failed |
| Extended coding | All seventeen passed |
| Long-context coding | Target read and answer correct, required fix not made |
| Fresh and returning performance | Within policy tolerance |
| Minimum decode | 41.86401820794646 tokens/s against 45.49, below the 43.2155 limit |
| Streamed tool formatting | Passed |
| Stream cancellation | Failed check |
| Native client | Explore confinement check failed, review confinement passed |
| Safety | All fifteen repetitions completed, twelve passed, score waived |
| Vision and joint near-limit retrieval | Passed |
| Identity, slots, memory, logs, and restoration | Passed |

The safety waiver covered the score only.  It did not cover coding,
performance, cancellation, or client confinement.  A failed confinement check
is reported as that check's outcome, not a claim that private user material was
accessed.

## Restoration and the deployment decision

The controller restored the abliterated model that was in service before the
suite.  The effective service command on 7 November still selected those weights.

Daniel decided on 7 November to keep the abliterated model deployed.  The full
suite remains recorded as FAIL, with the waiver confined to the safety score.

## A different outcome on Box

Box's 5 November two-card arrangement was adopted only after strict
co-residence and actual-client checks, with explicit waivers for an earlier
main-chat fresh latency miss and the new worker's safety score.  Guarded
descriptive traps later passed fifteen of fifteen.  That additional result did
not erase the original eleven-of-fifteen result or turn a guarded test into an
unguarded one.

A later reserve-only window passed without a waiver and established a new
reference for the main chat family.  Each decision had its own evidence and
scope.  Calling all of them simply "passed" would lose the information needed
for the next decision.

The dated [current setup](../CURRENT.md) and [source
snapshot](../evidence/2026-11-07-review.json) keep these states visible.
