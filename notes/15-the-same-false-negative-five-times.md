# The same false negative, five times

**Question.** A reasoning model returns an empty string.  The harness records a
failure.  How many times can one machine make that mistake?

**Verdict.** At least five, across four different harnesses, over three weeks —
and raising the token budget did not stop it.  The recurrence is the finding.
The defect was fixed each time in the harness that had just been caught, and the
default it was fixed to lived nowhere that the next harness could inherit it.

## The mechanism

A model that emits reasoning before its answer spends its output budget on the
reasoning first.  If the budget runs out there, the response comes back with a
finish reason of `length`, a populated reasoning field, and **content that is an
empty string**.

An empty string is not a wrong answer.  It is not an answer.  But it satisfies
almost any grader that is looking for the absence of something — it contains no
forbidden words, it matches no reject pattern, it is under any word limit — and
it fails every grader looking for the presence of something.  So it lands in the
results as an ordinary content failure, which is to say as a statement about the
model's capability.

## The five occurrences

| budget | where | what it looked like | what it was |
|---|---|---|---|
| 2,000 | eval suite | five tasks failed | budget |
| 4,500 | model comparison | candidate lost the bake-off, 2 failures | budget, ~16,000 characters of reasoning each |
| 500 | task-model gate | gate reported the model unfit | budget |
| 300 | coder benchmark | model scored as broken | budget |
| 16,000 | baseline row, re-checked a week later | incumbent lacked a capability | budget, 29,734 characters of reasoning |

The second one inverted a decision.  A bake-off between an incumbent and a
candidate concluded **keep the incumbent**; the comparison script had never
passed a token budget through, so the harness default starved the heavier
reasoner.  Both of its "failures" were empty content.  Re-run with a budget that
fits, the verdict reversed and the candidate was adopted.

Three of these happened in a single day, in three different harnesses.

The last one is the one that matters most, and it is the reason this note exists
rather than being a line in [note 09](09-when-the-harness-scores-itself.md).  It
happened at a budget of 16,000 — the number the earlier fixes had settled on as
generous.  **The budget was raised four times and the failure mode survived it.**

## Why raising the default is not the fix

There is no budget that is safe.  A model under greedy decoding can loop, and a
loop has no length.  Any fixed ceiling is a bet about the worst case, and the
worst case is unbounded.

Two changes actually hold:

**Score an empty response as its own outcome.**  Not a pass, not a content
failure — an error, counted in its own column.  This is the only reason any of
the five were diagnosable at all.  A suite that folds empties into failures
reports a capability gap and gives you nothing to notice.

**Record why it was empty, next to the row.**  The finish reason and the length
of the reasoning that was produced.  `EMPTY (finish=length, reasoning=29734c)` is
a different sentence from `EMPTY (finish=stop)`; the first is starvation and the
second is a model that genuinely said nothing.  Without that field, both read as
a blank cell.

The results file also now records the token budget and the sampling settings that
produced it, because two baselines on this machine do not, and "match the
baseline's settings" was therefore not a checkable instruction — the numbers had
to be argued about rather than read.

## Why it kept coming back

Every one of these was fixed the day it was found.  The fixes were real.  They
were also local: a constant in one script, a flag added to one call site, a
default changed in one harness.

Each new harness started from the same reasonable-looking small number, because
a small number is what you pick when you are thinking about the task rather than
about the model.  Two hundred tokens is plenty for a task whose correct answer is
the word `mode`.  It is nowhere near enough for a model that thinks for six
thousand words before saying `mode`.

**A fix that lives in an instance will be re-created as a bug in the next
instance.**  The thing that finally stopped it was not a larger constant.  It was
the empty-response accounting moving into the shared runner every harness calls,
so a new harness inherits the diagnosis even when it inherits the wrong budget.

## What generalises

- Distinguish "wrong answer" from "no answer" in the data structure, not in the
  commentary.  They have nothing in common except the number they produce.
- When a category of output can trivially satisfy your grader, that grader cannot
  be trusted on it.  An empty string passes every negative test ever written.
- A repeated bug is evidence about where the fix was put, not about how careful
  people are.  Ask which shared thing could have carried it.
- Any harness that caps generation is measuring the cap until proven otherwise.
  Print the cap in the output.
- The fifth occurrence was found by re-checking a stored baseline row rather than
  trusting it.  Stored results are documentation of a past run, not measurements
  of the present one — the same rule [METHOD](../METHOD.md) already applies to
  performance baselines applies to correctness rows.
