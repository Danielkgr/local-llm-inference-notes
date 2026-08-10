# Measurement rules

The rules this repository holds itself to.  Each one is here because breaking it
produced a wrong result that was about to be published, and most of the notes are
the record of that happening.

## Running a measurement

**Declare the noise band before the run, not after.**  Prefill plus or minus 5 per
cent, decode plus or minus 10 per cent.  A band chosen after seeing the numbers is
not a band, it is a rationalisation.

**Three samples plus a warm-up, medians reported, not means.**  One run is not a
trend.  A mean hides the outlier that tells you the run was contaminated.

**Record the spread, even when nobody asks for it.**  The median says what
happened; the spread says whether to believe it.  Two configurations in
[note 05](notes/05-the-control-that-killed-a-false-claim.md) were caught and
excluded because their decode spread jumped to about 15 while prefill stayed
steady, which is the signature of external contention rather than a real effect.

**Measure a control in the same sitting, even when a baseline is already
recorded.**  A performance number is bound to the method and the machine state
that produced it.  It is not a property of the configuration and it does not
keep.  Baselines older than the current sitting are documentation, not
measurements.  This rule exists because a week-old baseline turned a 3.4 per cent
null into an apparent 7 tok/s win.

**Alternate the arms rather than running them in blocks.**  Block-sequential A/B
on this machine fabricated a regression that interleaving disproved.  Thermal and
cache state drift over a session, and a block design aliases that drift onto the
variable under test.

**Give every prompt a per-request nonce.**  Prompt-cache hits on repeated
identical prompts produce nonsense prefill figures that look like enormous wins.

## Trusting a measurement

**Assert provenance in both directions.**  Before believing an A/B, read
`/proc/PID/maps` on both sides and confirm the loaded library trees are disjoint.
A benchmark that silently measures the same libraries twice returns a very
convincing null.

**Never attribute a delta measured across two different methods.**  Comparing a
number from one harness against a number from another measures the harnesses.
Several claims on this machine were retracted for exactly this.

**Check the apparatus could have produced a different answer.**  A result of
exactly zero, or exactly the maximum, usually indicts the harness rather than the
subject.  Identical failure text across unrelated categories means one shared
cause upstream of the thing being tested.  See
[note 09](notes/09-when-the-harness-scores-itself.md).

**Watch the spread of the whole field, not just the winner.**  When every
candidate lands within a few points of the maximum, the benchmark has stopped
measuring whatever its pass rate says.

## Correctness

**Correctness gates outrank speed.**  A faster configuration that changes the
output is not a faster configuration.

**Test the invariant the technique promises, not the output quality.**  Where a
method guarantees something structural, checking that guarantee is cheap, binary,
and not arguable, while quality evaluation is expensive, noisy, and easy to argue
with.  Greedy speculative decoding must be output-identical, so a single diff
settles it.  See [note 03](notes/03-speculative-decoding-is-lossy.md).

**Do not use a model to grade models.**  A judge makes the result depend on the
thing being measured.  Deterministic graders, and tasks written so short answers
are the only correct answers.

**Distinguish "wrong answer" from "no answer".**  An empty response is not a
failure of capability, and an empty string trivially satisfies any
does-not-contain check.  Count it separately or it will silently pass.

## Reporting

**Report negative and null results as plainly as positive ones.**  A measured null
is not an absence of information.  It is a forecast about the next decision, and
it can be checked later.

**Compare percentages, never raw scores, when the denominator changed.**  23 of 23
to 37 of 50 prints as "+14" while accuracy has fallen from 100 per cent to 74 per
cent.

**Name exactly which copy was verified.**  "The backup was checked" is not a
claim, it is a mood.  A verification claim that does not name the artefact it
checked has a way of turning out to describe a different one.

**Say when a number was measured under contaminated conditions, and exclude it.**
Do not quietly drop it.  The excluded rows and the reason belong in the note.

**A verifier that has never been seen to fail has not been tested.**  Exercise
every branch of a check against a known-bad input before trusting it.  Two
detectors on this machine passed their own self-tests while testing a copy of
their logic rather than the script itself.
