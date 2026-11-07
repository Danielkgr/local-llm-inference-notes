# Maintaining three local patches

Three local patches had different maintenance requirements.  A tensor dtype fix
merged upstream and became a regression check.  A vision sentinel fix stayed
local because the model needed to reproduce it had been removed.  A
request-default patch needed further changes when the client began sending
resolved server settings back as though the user had chosen them.

## Patch 1: a property that crashes, and the three conditions it needs

A GGUF loader node for the image stack defines a `dtype` property on its tensor
subclass.  For tensor types that torch handles natively it evaluates:

```python
return torch.Tensor(self).dtype
```

Constructing a `torch.Tensor` from a tensor that was created under
`torch.inference_mode()` raises:

```
RuntimeError: Inference tensors do not track version counter
```

The property access raises the exception.  The fix reads through the base class
descriptor without constructing another tensor:

```diff
-            return torch.Tensor(self).dtype
+            return torch.Tensor.dtype.__get__(self)
```

No copy, no version-counter interaction, same answer.

The reason this survived upstream for so long is that it needs three conditions
at once: a quantised UNET, a LoRA that patches bias keys, and a card
constrained enough to enter the low-VRAM path.  Only that path's VRAM estimator
reads `.dtype` on the bias tensors, and only plain F32 and F16 tensors take the
torch-compatible branch.  Anyone with enough VRAM never reaches the line.

This explains why a normally working loader could fail only on the constrained
configuration.  Users with enough VRAM did not enter the affected path.

## What upstreaming actually involved

The patch was carried locally from July, across several upstream releases, and
rebased once over a refactor without conflict.  Two things had to be
established before it was worth sending anywhere.

**Which repository owns the bug.**  The project is a fork.  The parent does not
have this bug.  Its equivalent file has no `dtype` property at all, so the
restructure in the fork introduced it.  Reporting to the parent would have been
noise.

**How to report it when the issue tracker is off.**  The fork has issues
disabled, so the report went as a pull request instead: one commit, one hunk,
with the repro path, the exception, and the version it was observed on.  It was
merged the same night.

## Updating the maintenance script

Carrying the patch meant carrying a helper that re-applied it after every
upstream pull, and could answer three questions without writing anything: does
it apply, is it already applied, has the file moved.

Once upstream merged it, that script's job reversed.  It no longer restores
anything.  It now asserts that the upstream fix is **still present** after each
pull, and fails if it is not.

That inversion is worth doing deliberately rather than deleting the script.
Upstream can lose a fix it absorbed, to a revert, a bad merge, or a refactor
that reintroduces the old expression, and the machine that suffered from the
bug originally is the machine best placed to notice.  The local patch file was
cut down to its remaining half, with the merge commit recorded in its header
and an explicit instruction not to re-apply the merged part.

## Patch 2: correct, unsubmitted, and kept anyway

The same loader injects a zero sentinel when a state dict lacks a vision tower,
so that a downstream classifier does not mistake a vision model for a plain
language model.  The guard that decides whether to inject tests one marker key,
under its prefixed name.

Some models ship a real tower under the un-prefixed naming.  Those pass the
guard because the prefixed key is absent, and the injection then overwrites a
real tensor with zeros.  An upstream refactor made this sharper rather than
milder, because the sentinel is now written to exactly the key a real tower
occupies.

The fix is to test both namings, so the guard skips injection whenever a real
tower is present under either convention.

The patch has not been submitted upstream.  The model that demonstrated it was
removed from this machine a week before the refactor landed.  There is no local
repro left, so there is nothing to defend a pull request with beyond code
reading, and a maintainer's time spent evaluating a guess is a cost imposed on
someone else.

It is still carried, because it is inert on everything currently served: none
of the live models carry either marker key, so the patched branch and the
upstream branch behave identically today.  That supports retaining it as a
local precaution.  It does not provide a current reproduction for an upstream
report.

## Patch 3: a predicate that had to be narrowed twice

The third patch is a different kind.  A local model-serving application builds
its load request from browser local storage, so a browser with no saved
per-model settings sends a bare request and silently loses the server-stored
configuration: untuned context length, no draft head, the wrong projector.  Two
clients, same model, different command lines, no error either way.

The patch fills in the stored configuration for bare requests, and leaves alone
any request that carries an explicit setting.  All of the difficulty is in the
word "explicit".

The first version treated any populated field as user intent.  That was wrong
after an upstream release began echoing the **resident model's resolved
values** back into the browser's own store.  After one tuned load, every
subsequent request from that browser carried a speculative-decoding field and a
cache type that the user had never chosen, and the patch dutifully treated them
as deliberate.  One tuned load poisoned every later load from the same browser:
untuned context, and on one model a crash from the wrong projector.

The narrowed predicate keeps only two fields as evidence of intent, and treats
the echoed ones as noise.  It also gained a diagnostic branch: when a stored
configuration exists but the request is *not* bare, it logs which fields
disqualified it.  Before that, a load that skipped the override was
indistinguishable in the logs from one that had no override to apply.

The predicate depended on which fields the client sent.  The upstream change
therefore required a review of the predicate as well as the server patch.

## Scope

The upstreamed fix is checked after updates.  The vision sentinel change
remains a local patch without a current reproducer.  The request-default patch
needs review whenever the client changes the fields it sends.
