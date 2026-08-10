# The control run that killed a result I was about to publish

**Question.** A 31B model was serving at 40960 context with 1.55 GiB of VRAM free,
which is uncomfortably thin on a 24 GB card.  Would a q4_0 KV cache buy back a
larger context, and possibly vision, without costing long-context recall?

**Verdict.** Yes on context.  But the decode "gain" the first pass appeared to
show was an artefact of comparing against a week-old number, and does not exist.

## Method

Test stanzas were clones of the live serving configuration with only
`--cache-type-k` and `--cache-type-v` changed, so KV type was the single
variable.  The live configuration was never touched.

Three details did real work:

- **Decode came from the inference server's own timings**, read from the upstream
  port, rather than wall-clock through the proxy in front of it.  The convenient
  in-house benchmark script measures through a different application on a
  different build, so it was deliberately not used.
- **Every prompt carried a per-request nonce.** This box has previously produced
  nonsense prefill figures from prompt-cache hits on repeated identical prompts.
  A nonce guarantees prefill is real work each time.
- **A same-sitting control was measured**, even though the brief said the
  baseline was already known and recorded.  That decision is the entire point of
  this note.

## The stale-baseline trap

| q8_0 at 65536 | decode (avg) |
|---|---|
| Recorded baseline, measured a week earlier | 58.3 tok/s |
| Same harness, same sitting, measured today | 63.22 tok/s |
| q4_0 at 65536, the configuration under test | 65.34 tok/s |

Against the recorded number, q4_0 looks like a 7 tok/s decode win.  Against the
control measured minutes earlier on the same harness, the honest delta is 2.1
tok/s, or 3.4 per cent, which sits inside the noise band.

**q4_0 KV is decode-neutral.  The win is purely VRAM.** Had the control been
skipped as redundant, this note would have reported a performance improvement
that does not exist, and it would have been reported in good faith.

The general form: a performance number is bound to the method and the machine
state that produced it.  It is not a property of the configuration, and it does
not keep.  Baselines older than the current sitting are documentation, not
measurements.

## What q4_0 actually bought

| config | VRAM | free | decode (best) |
|---|---|---|---|
| Live, q8_0 at 40960 | 22.43 | 1.55 | 59.1 |
| q4_0 at 65536 | 21.72 | **2.27** | 66.41 |
| q8_0 at 65536 (control) | 23.67 | 0.31 | 65.03 |
| q4_0 at 65536 with vision | 22.89 | 1.10 | 67.60 |

Sixty per cent more context and more free VRAM than the smaller configuration
had before.  On a card that was running at 98.7 per cent occupancy, that is the
whole result.

## Two rows I excluded rather than published

Partway through the session, decode spreads on two configurations jumped to
about 15 while prefill stayed steady at 551 tok/s.  Decode alone was affected and
both had ample free VRAM, so this was external GPU contention rather than memory
starvation.  The likely cause was an Electron desktop application holding a GPU
process on the same card.

Those two rows are marked contaminated and excluded from the conclusion.  The
deciding pair was measured before contention began, with spreads of 1.66 and
4.29, and stands.

Publishing a clean-looking number from a dirty run is the failure mode this
avoids.  The spread, not the median, is what exposed it, which is a reason to
record spread even when nobody asks for it.

## Pass criteria, written before the test

1. 65536 fits with at least 1 GiB free.  **Pass**, 2.27 GiB, criterion exceeded
   twice over.
2. Decode does not regress materially.  **Pass**, neutral against the same-sitting
   control.
3. Long-context recall holds on the evaluation suite.  **Pass**, long-context
   category improved from 5 of 6 to 6 of 6, overall 49 of 50, identical.  The
   control scored 6 of 6 as well, so the improvement is not attributable to q4_0.

Promoted on all three.

## The change I did not make

Vision fits.  It costs 1.17 GiB of the new headroom, leaving 1.10 GiB free, and
it works with no decode penalty.  It was still not restored.

The thin margin was the entire reason for removing vision a week earlier, and
the configuration notes record that this model is never sent images.  Spending
half the new headroom to buy back an unused capability is a bad trade, and the
session had just demonstrated that a stray GPU process can perturb this box.

The one-line change to reverse the decision is documented in place.  Knowing that
something fits is not a reason to fit it.
