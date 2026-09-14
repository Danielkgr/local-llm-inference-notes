# The approval gate that blocked its own linter

**Question.** An agentic coding harness had already been hardened: catastrophic
shell commands denied, read-only subagents stripped of their edit and shell
tools, and a health gate asserting the shape.  Two questions remained.  Was it
actually safe, and was it actually fast?

**Verdict.** Mixed, and the interesting failures were structural rather than
missing.  The denies worked exactly as documented.  But five of eleven agents
shared a backend serving a single slot, two models with recorded destructive
tool failures sat one click away in the model picker, the dominant language in
the tree had no language server at all, and the approval rule added during this
work blocked the linter it was added to protect.

## Harness

Read-only inventory of both machines first, then changes applied one at a time
with a timestamped backup per file and a live probe after every permission
change.  Nothing was accepted on inspection alone.  Permission behaviour in
particular is only ever confirmed by driving a real session, because this
harness has a documented shape where a rule that reads correctly in the config,
and resolves correctly in the API, still fails to enforce.

## Five agents, one slot

The primary coder ran on a 27B model served from a second machine.  Its serving
stanza set no `--parallel` flag, and the server defaults to one slot.  Five of
the eleven configured agents pointed at that model: the interactive builder, the
planner, an autonomous implementer, the code reviewer, and the summariser.

The reviewer is spawned by the builder as a child.  So a review request queued
behind its own parent's prompt evaluation, on a model holding 172,032 tokens of
context.  Summarisation and compaction did the same thing mid-session.  Nothing
errored.  The session simply went quiet, which is the worst possible
presentation for a queueing fault, because it reads as slowness rather than as
contention.

The second inference host next door was running a 35B agent model at three
slots, and idling.  Moving the reviewer and the summariser onto it cost nothing
and removed the contention entirely.

The general lesson is that agent routing and slot capacity are one decision, not
two.  A routing table that looks well spread across model names can still be
one queue.  Count slots, not models.

## Chat-only is a claim, not a control

Two models offered by the harness had failed a destructive-action probe on
record.  One called an explicitly forbidden `wipe_database` tool when told to
clear out test data.  The other did the same on a hard-tier task, reproducibly.

Local policy already covered this: a model that executes an explicitly forbidden
destructive action is not eligible for agent or tool duty, and may remain
chat-only only when every tool-bearing capability is disabled and that
containment is asserted by health checks.

No agent routed to either model, which felt like containment and was not.  The
global permission was allow, both models remained selectable from the picker,
and one of them was declared with tool calling explicitly enabled.  Containment
that depends on nobody choosing the wrong entry in a dropdown is not
containment.  Both were removed from the provider, and the health gate now
asserts their absence, so the claim is testable rather than remembered.

## Ordering is the whole of the permission model

Approval rules resolve last match wins.  The map therefore has to read: allow
everything, then the patterns that need approval, then the patterns that are
never allowed.  Get that order wrong and a broad allow silently overrides a
specific deny.

Two behaviours are worth writing down.  A rule that genuinely denies removes the
tool from the model's offer entirely, rather than rejecting the call when it
arrives.  And in a non-interactive run, a rule that asks for approval fails
closed and auto-rejects.  That is the right default, but it means a headless
invocation of this harness cannot push to a remote, which is a property to
choose deliberately rather than discover.

Every rule was verified by driving a session against a canary command that
exists only to be denied.  The refusal came back with the full resolved rule
list, which is the cheapest possible proof that the config on disk is the config
in force.

## The gate that blocked its own toolchain

The approval rules included one that asks before running any command mentioning
the shared tools directory.  The intent was to catch an agent reaching outside
its repository.

The Python linter and formatter installed during the same pass live in that
directory.  So the first smoke task failed to lint: the agent tried to run its
own quality gate, and its own approval rule stopped it.

The fix is one more rule, placed after the ask and before the denies, that
explicitly allows the read-only tool path.  Last match wins does the rest.  The
useful part is not the fix, it is the shape of the mistake.  A path-shaped
guardrail written against an abstract idea of "outside the repository" will
catch the toolchain, because the toolchain is also outside the repository.  Any
such rule needs an allowlist for the tools the agent is expected to run, written
at the same time, or the guardrail degrades the agent it protects.

There is a second, blunter limit here.  These rules match the command string,
not the filesystem path a command touches.  They can gate `git push`, `sudo`,
and commands that name a sensitive prefix.  They cannot reliably intercept an
arbitrary write to an absolute path.  It is worth stating that plainly rather
than describing the result as write protection.

## The blind spot was the main language

The tree held 257 Python files against 29 TypeScript and 10 TSX files.  The only
language server wired in was TypeScript, and automatic language server downloads
were disabled, so nothing was going to fix that on its own.  The agent could not
see a type error or an unused import in the language that made up most of the
work.  A linter and a language server, plus a pre-commit hook that runs the
formatter and the tests, is a smaller change than any model swap and a larger
one than most.

The hook needs one more thing to be a control rather than a suggestion: skipping
verification has to require approval too, or the agent can simply commit past
it.

## A backup that had been failing silently

Unrelated to the harness, and found only because a health check flipped from one
day stale to two days stale when the date rolled over: the daily snapshot job
had aborted for two consecutive nights.

The cause was an explicit file manifest that still named a service unit retired
some time earlier.  The archiver cannot stat the missing path, exits with status
2, and the job's error handler removes the incomplete snapshot.  The exit status
reached the journal.  The message explaining it did not.

Keeping the manifest explicit is still right, because a genuine loss should fail
loudly rather than be quietly skipped.  The missing discipline is the other half
of that bargain: when a listed path is retired, it has to be removed from the
manifest in the same pass.  A backup that fails loudly into a log nobody reads
is a backup that does not exist, and the only reason this surfaced at all was a
staleness check with a threshold low enough to fire before the loss mattered.

## What changed

The reviewer and the summariser moved to the idle three-slot host.  Two models
with recorded destructive failures left the provider, with the health gate
asserting it.  Approval rules now cover pushing, privilege escalation, named
sensitive prefixes, and skipping commit verification, with an explicit allow for
the tool path.  A Python language server, a linter, a formatter, and a
pre-commit hook went in.  House rules moved into the global agent instructions
so they apply outside one project tree.  The stale manifest entry came out of
the backup job.

Three smoke tasks then ran end to end through the harness rather than by hand: a
one-file bug fix took 63 seconds and produced a one-line diff, a two-file
refactor took 29 seconds and correctly dropped an import that became unused in
one file while keeping it in the other, and a web search task took 14 seconds
and returned a cited answer.  The pre-commit hook refused the commit while the
fixture test was failing, and passed once it was fixed.
