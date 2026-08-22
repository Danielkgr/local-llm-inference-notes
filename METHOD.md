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

**Measure the noise floor of a graded suite before comparing two configurations
on it.**  Repeat one configuration three times and see what moves.  Four sampling
profiles run three times each produced three different rankings from the same
twelve runs, and a three-point lead in the first sitting was gone by the third.
See [note 12](notes/12-four-sampling-profiles-three-rankings.md).

**Print the token budget in the output, and treat any capped run as measuring
the cap until shown otherwise.**  A reasoning model that runs out of budget
returns empty content with a finish reason of `length`, which reads as a wrong
answer.  Four different budgets produced four false capability findings here, and
the last of them was a budget already raised to be generous.  See
[note 15](notes/15-the-same-false-negative-five-times.md).

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

**A result that favours you needs the same control as one that does not.**  A
candidate that recovers a task the incumbent failed is making a claim about a row
in a stored baseline file.  Re-run that task against the incumbent in the same
sitting.  The first use of the adoption gate produced a recovery that was a token
budget running out a week earlier.  See
[note 13](notes/13-gating-on-the-failure-set.md).

**Check that a guard could fire before trusting it.**  Two on this machine could
not: a compaction threshold set beyond the context the server would accept, and
an early-abort that was requested alongside a concurrency setting which computed
every task before the first result was read.  A guard that cannot fire is worse
than no guard, because it is also a claim that you are guarded.  See
[note 11](notes/11-a-guard-that-trusts-its-own-number.md).

**Derive a limit from the thing it protects; never restate it in a client.**
Where a client insists on holding its own copy, assert equality against the
server at startup and refuse to run on mismatch.  A declared number that nobody
checks is a comment with consequences.

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
does-not-contain check.  Count it separately or it will silently pass.  Record
*why* it was empty next to the row — the finish reason and how much reasoning
was produced — because a starved budget and a model that said nothing are
different findings that print as the same blank cell.

**Compare failure sets, not totals, when the decision is adoption.**  A candidate
earns adoption by failing nothing the incumbent passes.  Only the tasks the
incumbent passed can disqualify it, which is also the cheapest way to run the
comparison.  See [note 13](notes/13-gating-on-the-failure-set.md).

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

**Label a partial run inside its own output.**  Any run that was filtered, gated,
or aborted must carry the selection that produced it, so a twelve-task gate can
never be read back later as a suite score.

## Changing the machine

**Anything underneath the engine is part of the apparatus.**  A graphics driver,
a kernel, an allocator: upgrading one invalidates every baseline you hold.  Take
fresh baselines first, or the next comparison becomes an argument about which
change caused what.

**A rejection is dated and conditioned.**  A candidate rejected under the old
driver has to be re-checked after the driver changes, because the rejection was
a fact about the pair, not about the candidate.

**Derive what is in use from the running configuration, not from a search for
its name.**  A grep answers "where does this string appear", which is a different
question from "what gets executed".  A build tree that appeared only in comments
was about to be deleted; a guard clause in the serving configuration executes it
for one model that nothing else can load.

**For a risky change you cannot supervise, make the proven configuration the
default and give the new one a single one-shot attempt with an automatic test
afterwards.**  Then a failure costs a reboot rather than a trip to the machine.
See [note 14](notes/14-six-upstream-bumps-rejected.md).

**A local patch needs a recorded base commit, a check that runs after every
pull, and a condition that ends it.**  Without the third it is permanent by
default.  When upstream absorbs the fix, invert the check rather than deleting
it: the machine that found the bug is the one that will notice its return.  See
[note 10](notes/10-carrying-a-patch-against-upstream.md).
