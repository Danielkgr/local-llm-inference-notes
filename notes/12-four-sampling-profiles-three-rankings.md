# Four sampling profiles, three repeats, three different rankings

**Question.**  Does the sampling profile a model is served under change how well
it scores, and by enough to justify changing it?

**Verdict.**  Not measurably, at three repeats.  Three of the four profiles landed
on exactly the same mean.  More usefully, running each profile three times
produced three different league tables from the same twelve runs, and the
profile that came last in the first sitting was joint first in the second.

## The design

One model, one 50-task graded suite, four sampling profiles, three repeats each.
Twelve complete runs.  The profiles were the one in production, the vendor's
published recommendation for non-thinking mode, a low-temperature variant, and
the production profile with a minimum-probability floor added.  That last one
earns its place because a `min_p` floor is supposed to trim the unlikely tail
and stabilise output.

| profile | temperature | top-p | top-k | min-p |
|---|---|---|---|---|
| production | 0.6 | 0.95 | 20 | 0.0 |
| vendor card, non-thinking | 0.7 | 0.80 | 20 | 0.0 |
| low temperature | 0.3 | 0.95 | 20 | 0.0 |
| min-p floor | 0.6 | 0.95 | 20 | 0.05 |

Graders are deterministic, so every point of variation between runs comes from
the model's own sampling.  This is the same suite described in
[note 08](08-a-benchmark-with-no-judge.md), run on the hard tier as well as the
core tier because the core tier ceilings.

## Result: the ranking is not stable

| profile | rep 1 | rep 2 | rep 3 | mean | spread |
|---|---|---|---|---|---|
| production | 45 | 45 | 45 | 45.00 | 0 |
| vendor card | 44 | 46 | 45 | 45.00 | 2 |
| low temperature | 47 | 46 | 46 | 46.33 | 1 |
| min-p floor | 45 | 46 | 44 | 45.00 | 2 |

Read the columns rather than the means:

- **Sitting 1** ranks low temperature first and vendor card last, three points
  apart.
- **Sitting 2** has vendor card, low temperature, and min-p tied at the top,
  with production alone at the bottom.
- **Sitting 3** puts low temperature first again, with min-p last.

Any one of those sittings, written up alone, is a finding.  A three-point gap on
a 50-task suite is six percentage points, which is the kind of number that gets
quoted.  It is a coin flip landing the same way twice.

The only claim the whole sweep supports is that **low temperature may be worth
more repeats**.  Its mean is 1.33 points above the other three, or 2.7 percentage
points, against a within-profile spread of up to 2 points.  That is suggestive at
three samples and nothing more.  Nothing here licenses a change to the served
configuration.

**The stabiliser did not stabilise.**  Adding a `min_p` floor to the production
profile, the one intervention with a mechanical story attached, produced the
joint-widest failure set and a spread of 2, against the unmodified profile's
spread of 0.  The hypothesis was reasonable and the measurement declines it.

## What is stable: the failure set, not the score

Recording per-task results rather than totals makes a second, much sharper
reading available.  Split every profile's failures into the tasks it failed on
**every** repeat and the tasks it failed on **any** repeat.

| profile | always fails | ever fails |
|---|---|---|
| production | 5 | 5 |
| vendor card | 4 | 7 |
| low temperature | 3 | 4 |
| min-p floor | 4 | 7 |

Across all four profiles and all twelve runs:

- **Three tasks fail every time, under every profile.**  One code task and two
  reasoning tasks.
- **Seven further tasks fail at least once somewhere**, and none of them fails
  consistently.
- The other forty pass everywhere.

So the whole 44-to-47 range across twelve runs is seven flip-prone tasks landing
differently.  The scores move; the model does not.

That reframes what the suite is for.  **A total is a noisy statistic; the
always-fail set is a property.**  Three tasks are the standing weakness of this
model at this quantisation, they are the same three regardless of how it is
sampled, and they are the only part of these twelve runs that would survive a
replication.

One further detail worth honesty about: the production profile returned an
identical score *and* an identical failure set on all three repeats.  That is the
strongest stability signal in the sweep, and it is still three samples at
temperature 0.6.  It is not determinism, and it should not be reported as
determinism.

Nine of the ten tasks that fail anywhere are from the hard tier.  That is the
tier doing its job.  The core tier had ceilinged and could no longer separate
anything, which is why the hard tier exists.

## What generalises

- **Repeat one configuration before comparing two.**  A benchmark's noise floor
  is a measurable property of the benchmark, and until it is measured, every gap
  is unfalsifiable.  Three repeats cost twelve runs here and dissolved a
  three-point finding.
- **Report the always-fail set alongside the score.**  It is the part that is
  about the subject.  A single run cannot distinguish a standing weakness from a
  bad sample, and the standing weakness is the actionable half.
- **A ranking that changes between sittings is not a ranking.**  If the order
  depends on which repeat you publish, publish the spread instead.
- A mechanism that predicts an improvement is a hypothesis, not a result.  The
  min-p floor had the best story of the four and the second-worst behaviour.
- Scores from this suite are comparable across machines; timings are not.  These
  runs were served from a different host than the recorded baselines, which is
  fine for pass rates and meaningless for tokens per second.
