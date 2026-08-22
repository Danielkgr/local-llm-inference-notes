# Six upstream bumps in a row, all rejected

**Question.** The inference engine has moved 149 tagged releases past the build
this machine runs.  Is staying put a maintenance failure?

**Verdict.** No.  Six consecutive candidates have been built, measured against
the live build on both arms, and rejected as flat or worse.  Two adjacent
upgrades in the same period, a graphics driver and a kernel, were adopted, and
both required the same measurement discipline as the engine bumps.

## The bump

The candidate was built from an upstream tag 149 tags ahead of the live build,
in a separate worktree, with the same build recipe, against the same Vulkan
backend.  Both binaries exist side by side; neither replaces the other until a
measurement says so.

The design is the one [METHOD](../METHOD.md) requires: paired arms, interleaved
rather than blocked, GPU otherwise idle, and run on two different serving shapes,
a dense model and one using multi-token prediction, because a change can help
one and hurt the other.

| arm | metric | live build | candidate | delta |
|---|---|---|---|---|
| dense | prefill | 2413.55 | 2414.66 | +0.0% |
| dense | decode | 117.86 | 116.72 | **-1.0%** (t = -6.76) |
| multi-token | prefill | 771.17 | 769.46 | -0.2% (t = -2.77) |
| multi-token | decode | 54.32 | 53.21 | **-2.0%** (t = -1.40) |

Note that the larger percentage regression is the worse-resolved one.  The dense
decode loss is small and unambiguous; the multi-token decode loss is twice the
size and does not clear a t of 2.  The verdict does not rest on either
individually.  It rests on the absence of any positive result anywhere in the
table, which is the sixth time in a row that has been the outcome.

**Draft acceptance was noisy between repeats** on the multi-token arm, from 0.77
to 0.84.  That is expected rather than alarming: that stanza serves at
temperature 1.0, so each repeat generates different text and drafts a different
number of tokens successfully.  It is precisely why the comparison is paired and
interleaved instead of block-sequential: the paired decode delta stays negative
regardless of where acceptance lands.

**The build no longer identifies itself.**  The binary now reports a generic
development version string, and its real identity lives only in the tag and
commit it was built from.  A version flag that returns the same answer for every
build is not a provenance check, and any harness that relied on one was
comparing labels rather than binaries.

## The near-miss: retiring an "unused" build

With the candidate rejected, three staged build trees were sitting on disk and
the obvious housekeeping is to delete the ones nothing references.

The first draft of that housekeeping recommended removing a build that a
grep of the serving configuration showed only in comments.  It is executed by a
guard clause in that configuration for exactly one model, whose architecture the
live build cannot load at all.  Deleting it would have silently killed that
model at its next load.

The check that would have caught it is the one
[note 07](07-when-the-verifier-is-wrong.md) already records: **derive from the
running configuration, not from a search for the name.**  A grep answers "where
does this string appear", which is a different question from "what executes
this".  One genuinely unreferenced tree was removed, recovering 1.4 GB.

## The driver upgrade is a performance change

A distribution point release of the Mesa packages arrived in the same period.
`mesa-vulkan-drivers` is the driver every llama.cpp process on this machine runs
through, so upgrading it invalidates every Vulkan baseline held.  That makes it a
measured change, not routine patching, and it was treated as one: fresh baselines
taken before, the same A/B repeated after.

| arm | metric | before | after |
|---|---|---|---|
| dense | prefill | 2413.55 | 2419.57 |
| dense | decode | 117.86 | 117.92 |
| multi-token | prefill | 771.17 | 766.55 |
| multi-token | decode | 54.32 | 54.52 |

All four inside the declared noise band, and the image pipeline's smoke test
passed.  The upgrade cost nothing measurable, which is the result that lets it be
adopted without a story.

Two things about it are worth recording anyway.  The update was **phased at ten
per cent** by the distribution, meaning it had not yet been rolled out widely.
Adopting it early is a choice, and it is the sort of choice that should be
written down before rather than discovered afterwards.  And the rejected engine
candidate was re-checked under the new driver and stayed rejected, because a
rejection measured under an old driver is a fact about the old driver.

## The kernel upgrade you cannot supervise

The kernel point release was the harder case.  This machine is the network
gateway for everything else, so a boot that hangs strands the whole stack, and
the person who would fix it was interstate.  A live-patch service covered the
running kernel for another year, so there was no urgency, only an outstanding
retest of a memory-management fix that had previously caused a hang class here.

Rather than defer it indefinitely, the reboot was made self-gating:

1. Install the new kernel packages, but leave the **default boot entry pinned to
   the proven kernel**, so any power cycle recovers on its own.
2. Set the new kernel as a **one-shot next-boot entry**.  It gets exactly one
   attempt.
3. Install a **self-removing post-boot unit** that runs the image pipeline's
   smoke test, a real render rather than a service ping, and pushes the verdict
   to a phone.
4. On failure, that unit **stays armed**.  The fallback boot re-runs the gate,
   and the repeat notification is itself the signal that the new kernel failed.

The reboot then becomes the last action of the session rather than a blocking
one, and no outcome requires a human at the machine.  The property that makes it
safe is that the *default* is the thing that already works, and the new thing has
to earn the default by passing a test after the fact.

## What generalises

- "Behind upstream" is not a defect.  Six rejections in a row are six pieces of
  evidence that this workload does not benefit, and each is a forecast that can
  be checked when the seventh arrives.
- Measure a bump on more than one serving shape.  A change that is flat on dense
  decode can still cost a speculative path.
- A delta's size and its resolution are separate facts.  Report both; do not let
  a large unresolved number carry a verdict on its own.
- Anything underneath the engine, whether driver, kernel, or allocator, forms
  part of the measurement apparatus.  Upgrading it invalidates the baselines,
  so take fresh ones first, or the next comparison becomes an argument about
  which change caused what.
- A rejection is dated and conditioned.  Re-check it after you change the layer
  underneath.
- For an unsupervised risky change, make the *proven* configuration the default
  and give the new one a single one-shot attempt with an automatic test
  afterwards.  A failure then costs a reboot rather than a trip.
