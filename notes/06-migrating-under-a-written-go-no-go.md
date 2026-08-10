# Migrating the whole stack under a written go/no-go

**Situation.** An LTS-to-LTS operating system upgrade on the single machine that
serves every model, runs the image pipeline, and holds the configuration. Two
technical blockers had been carried for weeks: a kernel regression that hung
image generation, and a Python version bump that would force every virtual
environment to be rebuilt.

**Approach.** Write the decision down before making it, in a document with a
verdict, a trigger condition, a rollback, and an ordered verification list. Then
execute against that document rather than against judgement on the day.

## The verdict was not "go" or "no-go"

It was **staged go**: everything on the machine is ready, and the trigger has not
fired yet.

Both technical blockers collapsed during the audit itself. The kernel regression
turned out to be resolved, and the environment rebuild turned out to involve five
environments rather than the six the earlier notes claimed. What remained was not
a technical gate at all. It was the vendor's own stability flag, which had not
yet flipped to mark the release supported for LTS upgraders.

Separating "the box is ready" from "the world is ready" is what made the document
useful. The work could be completed and verified while the decision stayed open.

## The trigger is a script, not a memory

The remaining gate was reduced to a single command that checks the vendor's
release metadata for the supported flag, with an optional weekly timer. A gate
that depends on someone remembering to look is not a gate.

The document also records what jumping the gate would mean, in plain terms:
running a release the vendor has not yet marked ready, on the machine that serves
everything, with no vendor driver repository for it yet. It will probably work,
and if it does not, the only way back is the image described below.

**The gate was then jumped deliberately.** The flag had not flipped when the
upgrade ran. That is the outcome the document was written to make possible: not
to force patience, but to ensure that going early was a decision taken against a
written description of the risk and a rollback that already existed, rather than
a decision taken on the day because the work felt finished.

A go/no-go that can only ever say "wait" is a delay mechanism. A useful one
states the cost of each branch and lets you choose the expensive branch with your
eyes open.

## Rollback first, and honestly

The pre-upgrade sequence runs before anything is touched:

1. A full backup including the compiled builds and virtual environments, not just
   the weekly one, which omits them.
2. **A root disk image, which is the only real rollback.** The system partition
   carries the configuration and the database as well as the OS, so one image
   covers everything. It requires booting external media, which means being
   physically at the machine.
3. Only then, the routine package upgrade, plus a same-sitting performance
   baseline captured before any change.

The document names the fallback for taking the image without a reboot, and says
plainly that it is messier and restores onto a fresh install. An honest rollback
plan describes the bad option too, because the day you need it is the day you
will not want to discover it does not exist.

The baseline capture carries its own warning: close the desktop application whose
GPU process perturbs decode measurements. A baseline taken carelessly is worse
than no baseline, because it will be trusted later.

## Verification is a list, in order, written in advance

Eleven steps, sequenced so that failures surface in dependency order: boot and
driver gates first, then network and remote access, then rebuild environments,
then each service individually, then the model serving layer, then the
end-to-end paths, then the periodic jobs, and finally the small things that
historically break on reboot.

One entry earns its place by what it concedes:

> the evaluation suite catches regression only, and cannot prove equivalence

That is the correct claim for a fixed task suite, and stating it inside the plan
stops a passing run from being read as proof the migration changed nothing.

## Outcome

The upgrade ran across two days, ahead of the vendor's own readiness flag. The
environments were rebuilt on a standalone interpreter. The kernel
image-generation hang was resolved rather than worked around.

The driver stack, which had been the largest perceived risk, was a non-event.
That was not luck: an [earlier evaluation](01-rocm-714-evaluation.md) had
measured that tier and found nothing, and predicted this outcome in writing
weeks beforehand.

One thing the plan did not anticipate: the new release renumbered the NVMe
devices. Device names are not stable identifiers across major versions, which is
the kind of finding that only arrives by doing it.
