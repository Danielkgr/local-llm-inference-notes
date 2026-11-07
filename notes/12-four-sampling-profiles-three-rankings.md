# Sampling profiles and repeatability

Four sampling profiles were tested three times each on the same fifty-task
suite.  The rankings changed between repeats.  Three profiles had the same
mean, and the low-temperature profile's small lead did not justify changing the
served configuration on this evidence.

## The design

One model, one 50-task graded suite, four sampling profiles, three repeats
each.  Twelve complete runs.  The profiles were the one in production, the
vendor's published recommendation for non-thinking mode, a low-temperature
variant, and the production profile with a minimum-probability floor added.
The `min_p` arm tested whether removing low-probability tokens would make
results more stable.

| profile | temperature | top-p | top-k | min-p |
|---|---|---|---|---|
| production | 0.6 | 0.95 | 20 | 0.0 |
| vendor card, non-thinking | 0.7 | 0.80 | 20 | 0.0 |
| low temperature | 0.3 | 0.95 | 20 | 0.0 |
| min-p floor | 0.6 | 0.95 | 20 | 0.05 |

The graders were unchanged and deterministic.  The experiment varied sampling
profiles, although execution variability cannot be ruled out solely from the
grader design.  This is the same suite described in [note
08](08-a-benchmark-with-no-judge.md), run on the hard tier as well as the core
tier because the core tier ceilings.

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

Any one of those sittings, written up alone, is a finding.  A three-point gap
on a 50-task suite is six percentage points, which is the kind of number that
gets quoted.  Three repeats did not resolve that gap reliably.

Low temperature had the highest mean and could warrant further investigation.
Its mean is 1.33 points above the other three, or 2.7 percentage points,
against a within-profile spread of up to 2 points.  Three samples were
insufficient to justify changing the served configuration.

The min-p arm had a joint-widest failure set and a spread of two points,
against the production profile's spread of zero.  It did not improve stability
in these runs.

## Per-task results

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

The 44-to-47 range was accounted for by seven tasks whose outcomes varied
across the twelve runs.

Three tasks failed in every observed run.  They are the most consistent
failures in this sample.  Further repetitions could still change that set.

The production profile also returned an identical score *and* an identical
failure set on all three repeats.  That is the strongest stability signal in
the sweep, and it is still three samples at temperature 0.6.  It is not
determinism, and it should not be reported as determinism.

Nine of the ten tasks that fail anywhere are from the hard tier.  The hard tier
supplied most of the observed differences.  The core tier had already reached
its ceiling.

## Scope

The served sampling profile stayed unchanged.  These twelve runs support
reporting the observed spread and per-task failures, but they do not establish
a permanent ranking or guarantee the same result on another backend or machine.
