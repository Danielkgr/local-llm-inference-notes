# Planning the operating system migration

The operating system migration had two known risks.  A kernel regression had
hung image generation, and the new Python version would require the virtual
environments to be rebuilt.  The machine also held the serving configuration
and databases.

I prepared a written decision, rollback, and ordered verification list before
upgrading.  The upgrade went ahead before the vendor's LTS readiness flag had
changed.  That was an explicit decision under the plan.

## Readiness and timing

It was **staged go**: everything on the machine is ready, and the trigger has
not fired yet.

Both technical blockers collapsed during the audit itself.  The kernel
regression turned out to be resolved, and the environment rebuild turned out to
involve five environments rather than the six the earlier notes claimed.  What
remained was not a technical gate at all.  It was the vendor's own stability
flag, which had not yet flipped to mark the release supported for LTS
upgraders.

Separating "the box is ready" from "the world is ready" is what made the
document useful.  The work could be completed and verified while the decision
stayed open.

## The trigger is a script, not a memory

The remaining gate was reduced to a single command that checks the vendor's
release metadata for the supported flag, with an optional weekly timer.  A gate
that depends on someone remembering to look is not a gate.

The document also records what jumping the gate would mean, in plain terms:
running a release the vendor has not yet marked ready, on the machine that
serves everything, with no vendor driver repository for it yet.  It will
probably work, and if it does not, the only way back is the image described
below.

**The gate was then jumped deliberately.**  The flag had not flipped when the
upgrade ran.  That is the outcome the document was written to make possible:
not to force patience, but to ensure that going early was a decision taken
against a written description of the risk and a rollback that already existed,
rather than a decision taken on the day because the work felt finished.

The plan allowed an early upgrade while recording the unsupported-release risk
and the recovery steps that decision required.

## Rollback

The pre-upgrade sequence runs before anything is touched:

1. A full backup including the compiled builds and virtual environments, not just
   the weekly one, which omits them.
2. **A root disk image, which is the only real rollback.**  The system partition
   carries the configuration and the database as well as the OS, so one image
   covers everything.  It requires booting external media, which means being
   physically at the machine.
3. Only then, the routine package upgrade, plus a same-sitting performance
   baseline captured before any change.

The document names the fallback for taking the image without a reboot, and says
plainly that it is messier and restores onto a fresh install.  The plan
recorded the limitations of that fallback.

The baseline capture carries its own warning: close the desktop application
whose GPU process perturbs decode measurements.  A baseline taken carelessly is
worse than no baseline, because it will be trusted later.

## Verification is a list, in order, written in advance

Eleven steps, sequenced so that failures surface in dependency order: boot and
driver gates first, then network and remote access, then rebuild environments,
then each service individually, then the model serving layer, then the
end-to-end paths, then the periodic jobs, and finally the small things that
historically break on reboot.

The plan also limited the claim made for its evaluation suite.

> the evaluation suite catches regression only, and cannot prove equivalence

A passing fixed suite would establish the observed checks, not equivalence
across every workload.

## Outcome

The upgrade ran across two days, ahead of the vendor's own readiness flag.  The
environments were rebuilt on a standalone interpreter.  The kernel
image-generation hang was resolved rather than worked around.

The driver change did not cause the expected migration difficulty.  An [earlier
evaluation](01-rocm-714-evaluation.md) had found no material change on its
tested workloads.  The migration result was consistent with that finding.

One thing the plan did not anticipate: the new release renumbered the NVMe
devices.  Device names are not stable identifiers across major versions, which
is the kind of finding that only arrives by doing it.
