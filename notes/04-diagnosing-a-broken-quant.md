# Investigating a suspect 4-bit quantisation

A newly published 4-bit quantisation of a 27B model loaded without warnings,
then repeated a single token.  The immediate question was whether to adjust the
sampler, correct the template, or replace the file.

The file was replaced after degeneration persisted under greedy decoding, with
thinking enabled and disabled, and with the corrected chat template.

## What the greedy check established

Temperature zero removed sampling randomness from the diagnosis.  Repetition
under that setting showed that random token selection was not necessary to
produce the failure.  It helped avoid spending more time sweeping sampler
settings on this file.

The original version of this note went further and said that one greedy call
proved the weights were broken.  That was too strong.  A runtime defect, wrong
template, tokenizer mismatch, numerical fault, or deterministic decoding path
can also fail at temperature zero.  Changing repetition controls can affect a
greedy run as well.  Greedy decoding alone does not distinguish those causes.

The tests here supported replacing this suspect quantisation.  They did not
include a published tensor-level audit proving which conversion step caused the
failure.

## A possible quantisation failure

The model combines attention blocks with smaller state-space tensors.  Those
tensors can require higher precision than the larger matrices in a mixed
quantisation.  Reducing sensitive tensors too far is a plausible cause of a
file loading successfully and failing during generation.

That mechanism needs confirmation for a particular file.  The useful comparison
would keep the runtime, template, tokenizer, and request fixed while checking a
known-good quantisation or source weights.  The evidence recorded here does not
justify treating every repetitive 4-bit model as the same conversion defect.

## Other symptoms found during the investigation

| Symptom | Next check |
|---|---|
| Repetition persists at temperature zero | Inspect the deterministic path, template, runtime, and file identity.  Compare with known-good weights if available. |
| Repetition disappears after sampling changes | Check the recommended sampler and repetition controls.  This does not establish that all other configuration is correct. |
| Content is blank | Inspect finish reason and reasoning content before treating it as a wrong answer. |

A merged model also returned blank content while looping in its reasoning
field.  The template was not the immediate problem.  Adding repetition control
stopped the loops but damaged prose by removing function words.  Using the
published sampler values was the eventual configuration change.

Roughly a day had gone into sampler and template changes before the suspect
file was replaced.  The short greedy check would have narrowed the work much
earlier.  It would not, on its own, have proved the cause.
