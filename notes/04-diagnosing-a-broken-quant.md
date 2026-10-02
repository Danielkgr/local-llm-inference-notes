# Broken weights or bad config? One greedy call tells you

**Problem.**  A newly published 4-bit quantisation of a 27B model loaded with no
warnings, then degenerated into a repeated single token.  The obvious suspects
were sampler settings, the chat template, or the quantisation itself.  Each has a
different and expensive fix.

**The test.**  Send one short prompt at temperature 0.

Greedy decoding removes the sampler from the equation entirely: at temperature 0
there is no randomness left for a repetition penalty, a top-k, or a min-p value
to be misconfigured against.  If the model still degenerates, the fault is in the
weights.  No sampler adjustment and no template swap can recover it, so the
correct action is to discard the file rather than tune it.

In this case degeneration persisted at temperature 0, with thinking mode on and
off, and with a corrected chat template.  The quant was bad.  It was replaced
rather than debugged.

## Why that particular quant broke

The model uses a hybrid attention architecture with small state-space tensors
alongside the usual attention blocks.  Those tensors are numerically sensitive
and need to be held at higher precision, typically Q8_0 or Q6_K, even inside a
4-bit mixed quantisation.  Publishers who do this say so explicitly in the model
card.  A straight uniform conversion to 4-bit destroys the linear-attention
blocks while leaving a file that loads cleanly and reports nothing wrong.

That is the trap worth naming: the failure appears at generation time, not load
time, so nothing in the startup log warns you.

## The decision rule

| symptom | at temp 0 | conclusion |
|---|---|---|
| Repetition or degeneration | still present | broken weights, discard |
| Repetition or degeneration | disappears | sampler configuration, fix flags |
| Empty output, content field blank | still empty | inspect the reasoning field before assuming failure |

The third row cost a separate session.  A merged model returned empty responses
that looked like a broken chat template.  The template was fine: the model was
looping inside its reasoning field and never reaching the content field.  The
signal that separates the two is whether a reasoning field is present and
populated, not whether the content field is empty.

A related lesson from the same model: a merge shipped with no repetition control
in its serving configuration will loop where the base model does not.  Adding
repetition control fixed the loops but damaged prose, stripping function words
out of formal writing.  The eventual fix was neither, and was simply to use the
sampler values the model card specified.

## Cost of not having this rule

Before this rule existed, roughly a day went into sampler sweeps and template
swaps against a file that could never have worked.  The test that would have
settled it takes one API call and about two seconds.
