# Every speculative decoding variant that went faster changed the output

**Question.** llama.cpp offers several n-gram speculative decoding modes. Some
of them showed large throughput gains on a production model. Were the gains real?

**Verdict.** No. Greedy speculative decoding must be output-identical to greedy
decoding by construction. Every variant that produced a speedup diverged from
the baseline text, so none were adopted.

## The check that mattered

Speculative decoding drafts tokens with a cheap model or heuristic and verifies
them with the real one. Under greedy sampling the verification step guarantees
the accepted sequence matches what the target model would have produced alone.
Speed changes; text does not.

That gives a free correctness oracle: run greedy, diff the output against the
non-speculative baseline, and any difference means the implementation is not
doing what it claims. Because the guarantee is structural, a single diff settles
it. No quality evaluation, no judging, no scoring.

## Result

| variant | decode | against base | greedy output against baseline |
|---|---|---|---|
| none | 129.3 tok/s | baseline | reference |
| ngram-cache | 80.3 tok/s | -38.0% | harmful regardless |
| ngram-map-k | 142.9 tok/s | +4.4% | **diverges at char 118** |
| ngram-map-k4v | 150.7 tok/s | +15.9% | **diverges at char 118** |
| ngram-simple | 160.0 tok/s | +22.1% | **diverges, stops early at 205 tok** |
| ngram-mod | 204.3 tok/s | +57.8% | **truncated prefix, 213 tok against 300** |

The fastest variant looked like a 58 per cent win. It was dropping content: the
generated summary lost a clause present in the baseline. That is lossy
acceleration, not free throughput.

`ngram-cache` was separately shown to be actively harmful on two different
models, at -31 and -38 per cent, which moved an earlier neutral verdict to a
negative one.

## What generalises

Look for the invariant that the technique promises, and test that rather than
the output quality. Quality evaluation is expensive, noisy, and easy to argue
with. An invariant is cheap, binary, and not arguable.

Where such an invariant exists, checking it should be a required step in the
benchmark harness rather than a follow-up, because these variants were fast
enough to be tempting and were sitting one flag away from production.
