# N-gram speculative decoding changed the output

Several n-gram speculative decoding variants improved the reported decode rate
but changed the output in the controlled greedy comparison.  None were adopted.
The fastest variant stopped early and omitted content from the reference.

## The check that mattered

Speculative decoding drafts tokens and checks them against the target.  This
experiment used a controlled greedy comparison with ordinary decoding.  The
identity check required the target, sampler, and numerical execution conditions
to remain controlled.  A difference under those conditions failed the check,
without needing a model judge.

## Result

| variant | decode | against base | greedy output against baseline |
|---|---|---|---|
| none | 129.3 tok/s | baseline | reference |
| ngram-cache | 80.3 tok/s | -37.9% | harmful regardless |
| ngram-map-k | 142.9 tok/s | +10.5% | **diverges at char 118** |
| ngram-map-k4v | 150.7 tok/s | +16.6% | **diverges at char 118** |
| ngram-simple | 160.0 tok/s | +23.7% | **diverges, stops early at 205 tok** |
| ngram-mod | 204.3 tok/s | +58.0% | **truncated prefix, 213 tok against 300** |

Percentages were recalculated on 7 November 2026 against the displayed 129.3
tokens/s reference.  The original percentage column was inconsistent with that
reference.  The recorded rates are unchanged.

The fastest variant looked like a 58 per cent win.  It was dropping content:
the generated summary lost a clause present in the baseline.  That is lossy
acceleration, not free throughput.

`ngram-cache` was separately shown to be actively harmful on two different
models, at -31 and -38 per cent, which moved an earlier neutral verdict to a
negative one.

## Scope

The result applies to these n-gram implementations, target configuration, and
controlled greedy comparison.  It does not establish that speculative decoding
is inherently lossy.  A cross-backend or different-precision comparison needs
its own numerical controls.
