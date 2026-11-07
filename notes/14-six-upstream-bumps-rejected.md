# Six rejected engine updates

Six successive engine candidates were measured and rejected as flat or worse on
the tested workloads.  The detailed comparison below is the sixth candidate.  A
Mesa update and kernel update were also considered during the period.

These are historical experiments, using the paired protocol then in force.  The
current reference-reuse and qualification procedure is in
[METHOD.md](../METHOD.md).

## The bump

The candidate was built from an upstream tag 149 tags ahead of the live build,
in a separate worktree, with the same build recipe, against the same Vulkan
backend.  Both binaries exist side by side; neither replaces the other until a
measurement says so.

The historical design used paired arms, interleaved rather than blocked, GPU
otherwise idle, and run on two different serving shapes, a dense model and one
using multi-token prediction, because a change can help one and hurt the other.

| arm | metric | live build | candidate | delta |
|---|---|---|---|---|
| dense | prefill | 2413.55 | 2414.66 | +0.0% |
| dense | decode | 117.86 | 116.72 | **-1.0%** (t = -6.76) |
| multi-token | prefill | 771.17 | 769.46 | -0.2% (t = -2.77) |
| multi-token | decode | 54.32 | 53.21 | **-2.0%** (t = -1.40) |

Note that the larger percentage regression is the worse-resolved one.  The
dense decode loss is small with a larger reported t statistic; the multi-token
decode loss is twice the size and does not clear a t of 2.  The verdict does
not rest on either individually.  It rests on the absence of any positive
result anywhere in the table, which is the sixth time in a row that has been
the outcome.

**Draft acceptance was noisy between repeats** on the multi-token arm, from
0.77 to 0.84.  That is expected rather than alarming: that stanza serves at
temperature 1.0, so each repeat generates different text and drafts a different
number of tokens successfully.  It is precisely why the comparison is paired
and interleaved instead of block-sequential: the paired decode delta stays
negative regardless of where acceptance lands.

**The build no longer identifies itself.**  The binary now reports a generic
development version string, and its real identity lives only in the tag and
commit it was built from.  A version flag that returns the same answer for
every build is not a provenance check, and any harness that relied on one was
comparing labels rather than binaries.

## The near-miss: retiring an "unused" build

With the candidate rejected, three staged build trees were sitting on disk and
the obvious housekeeping is to delete the ones nothing references.

The first draft of that housekeeping recommended removing a build that a grep
of the serving configuration showed only in comments.  It is executed by a
guard clause in that configuration for exactly one model, whose architecture
the live build cannot load at all.  Deleting it would have silently killed that
model at its next load.

The check that would have caught it is the one [note
07](07-when-the-verifier-is-wrong.md) already records: **derive from the
running configuration, not from a search for the name.**  A grep answers "where
does this string appear", which is a different question from "what executes
this".  One unreferenced tree was removed, recovering 1.4 GB.

## The driver upgrade is a performance change

A distribution point release of the Mesa packages arrived in the same period.
`mesa-vulkan-drivers` is the driver every llama.cpp process on this machine
runs through, so upgrading it invalidates every Vulkan baseline held.  That
makes it a measured change, not routine patching, and it was treated as one:
fresh baselines taken before, the same A/B repeated after.

| arm | metric | before | after |
|---|---|---|---|
| dense | prefill | 2413.55 | 2419.57 |
| dense | decode | 117.86 | 117.92 |
| multi-token | prefill | 771.17 | 766.55 |
| multi-token | decode | 54.32 | 54.52 |

All four inside the declared noise band, and the image pipeline's smoke test
passed.  The upgrade cost nothing measurable, which is the result that lets it
be adopted without a story.

The rollout status also mattered.  The update was **phased at ten per cent** by
the distribution, meaning it had not yet been rolled out widely.  Adopting it
early is a choice, and it is the sort of choice that should be written down
before rather than discovered afterwards.  And the rejected engine candidate
was re-checked under the new driver and stayed rejected, because a rejection
measured under an old driver is a fact about the old driver.

## Unsupervised kernel upgrade

The kernel point release was the harder case.  This machine is the network
gateway for everything else, so a boot that hangs strands the whole stack, and
the person who would fix it was interstate.  A live-patch service covered the
running kernel for another year, so there was no urgency, only an outstanding
retest of a memory-management fix that had previously caused a hang class here.

The alternative to deferring it indefinitely was a reboot that gates itself:

1. Install the new kernel packages, but leave the **default boot entry pinned to
   the proven kernel**, so any power cycle recovers on its own.
2. Set the new kernel as a **one-shot next-boot entry**.  It gets exactly one
   attempt.
3. Install a **self-removing post-boot unit** that runs the image pipeline's
   smoke test, a real render rather than a service ping, and pushes the verdict
   to a phone.
4. On failure, that unit **stays armed**.  The fallback boot re-runs the gate,
   and the repeat notification is itself the signal that the new kernel failed.

This retained the proven kernel as the default after the one-shot attempt.  It
reduced the need for physical recovery but could not guarantee recovery from
every boot or hardware failure.

## Scope

These were decisions about the tested build, driver, configuration, and
workload.  They do not establish that later releases should be rejected.  The
current setup and test procedure are in [CURRENT.md](../CURRENT.md) and
[METHOD.md](../METHOD.md).
