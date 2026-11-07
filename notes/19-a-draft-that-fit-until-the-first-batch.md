# A draft that fit until the first batch

Three DFlash attempts ran on Strix on 1 November 2026.  The first two exhausted
command-submission memory at the production context.  A separately authorised
smaller-context arm loaded, then aborted during cancellation.  None qualified
or changed production.

## Load success was the wrong boundary

The incumbent was HaloBox 66da654-cve1 with a 35B-A3B Q6_K target.  The first
attempt added the Q8_0 DFlash draft at the existing total context of 786,432.
At its first batch, GTT use reached about 43.9 of the configured 44 GiB and
command submission failed with a Vulkan device-lost exception.

A second authorised attempt reduced the draft sequence setting from 15 to 4.
It hit the same first-batch failure.  A changed sequence count did not solve
the memory accounting gap.

The third arm halved total context to 393,216, or 131,072 per slot.  It was
measurement-only because that was no longer the lane's context contract.  It
loaded and peaked near 40.53 GiB GTT, making the draft's compute and
dense-layer KV costs visible.

## Acceptance was not acceleration

Before the abort, the draft accepted roughly 0.62 to 0.71 of drafted tokens.
That sounded promising.  Matched long-context decode was about 44.3 tokens per
second against 46.15, and fresh prefill took about 77.6 seconds against 73.3.
Those rounded values describe this smaller-context arm, not a qualified result
at the production context.  Some short requests improved, but they did not
establish a general speedup.

The stream-cancel canary then aborted the engine with an invalid token entering
the batch after cancellation.  The record supports a defect in the DFlash
cancellation path.  It does not prove the exact internal cause.  Subsequent
requests reached a dead server and are incomplete coverage, regardless of the
FAIL labels printed by the old report.

## Recovery was its own result

The recorded restoration returned the target to its original total context of
786,432, verified binary identity and the resource contract, and found no owned
survivors.  The 7 November effective command has no DFlash draft enabled.

The deciding checks were memory at first useful work and cancellation after
work began.  A successful load and a high acceptance ratio could establish
neither.  Further work needs changed implementation and memory evidence, plus
new authorisation.

Source hashes for all three attempts and the final interpretation are in the
[review evidence](../evidence/2026-11-07-review.json).
