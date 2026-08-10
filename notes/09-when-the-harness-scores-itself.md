# Two eval runs that scored the harness instead of the model

**Question.** A model scores 0/50 on one run and 44/50 on another.  How do you
know either number is about the model?

**Verdict.** Neither was.  Both results came from the harness, and both would
have been quoted as capability findings if the failure rows had not been recorded
alongside the scores.

## Case one: a perfect zero

One run recorded 0/50, with every one of the 50 tasks failing identically:

```
API: HTTP Error 404: Not Found
```

The same model had scored 2/2 on a smoke run thirty-five minutes earlier, so it
was registered and answering.  The stored result explains the difference.  The
run's model key is not a model name, it is two of them:

```
08. Model-A-27B (variant-tag, MTP Q4_K_M),09. Model-B-27B (variant-tag, MTP Q5_K_M)
```

Model identifiers are replaced with placeholders here.  The structure is
verbatim: two names, each already containing a comma, joined by a third.

Model names on this server contain commas.  A comma-separated list of two models
and a single model whose name contains a comma are the same string, and the
harness resolved it the wrong way, then asked the server for one model with a
very long name.  Every task 404ed.

A score of exactly zero across every task and every category is not a model
result.  No model fails a word-count task and a JSON task and a substring task in
the same way.  Identical failure text on all 50 rows is a harness signature.

## Case two: a plausible number

The second case is the dangerous one, because 44/50 is a believable score.

Six of the failures were not wrong answers.  They were empty:

| task | finish reason | reasoning emitted |
|---|---|---|
| code-04 | length | 16,920 chars |
| instruct-02 | length | 13,994 chars |
| faith-02 | length | 16,239 chars |
| hard-faith-04 | length | 15,397 chars |
| hard-instruct-02 | length | 17,353 chars |
| hard-instruct-04 | length | 20,612 chars |

The model spent its entire budget on `reasoning_content` and returned no content
at all.  The harness had temperature hardcoded to 0, which is structurally unable
to measure a model that loops under greedy decoding.  Run at its own recommended
sampling, on the same 50 task suite, the same model scored **50/50 with zero
errors**.

A 12 per cent gap was reported as a capability difference.  It was a sampling
choice belonging to the harness.

**Sourcing caveat.** Those two runs do not record their sampling settings.  The
attribution rests on the file naming and the harness's own change history, not on
the result files.  That is a real weakness in the evidence, and it is exactly the
weakness the third fix below addresses.

## What changed

Three fixes, all in the harness rather than the tasks:

1. **Validate model names against the server.**  Query the served model list, and
   only split a string on commas when every resulting part names a real model.
   Otherwise treat it as one name.  The ambiguity cannot be resolved by parsing
   alone, so it is resolved by asking.
2. **Make sampling a parameter, not a constant.**  Forcing one preset on every
   model measures how well each tolerates that preset, not how capable it is.
   The default stays at temperature 0 so old baselines remain comparable.
3. **Record the run's configuration in its own output.**  Endpoint and sampling
   are written into the results file, so a future comparison never has to
   reconstruct them from a filename.

Empty content was already counted separately from a wrong answer, which is the
only reason case two was diagnosable at all.  Had those six rows been scored as
ordinary failures, 44/50 would have looked like a model that is bad at
instruction following.

## What generalises

Record enough per-item detail to tell your own failures from the subject's.  A
score alone cannot distinguish "the model answered incorrectly" from "the model
never answered" from "the request never arrived", and those three have nothing in
common except the number they produce.

Two cheap signatures are worth watching for.  A result of exactly zero, or exactly
the maximum, usually indicts the harness rather than the subject.  Identical
failure text across unrelated categories means one shared cause upstream of the
thing being tested.

The general form: before believing a measurement, check that the apparatus was
capable of producing a different one.
