# A guard that trusts the number it was given

**Question.** An agentic client has automatic context compaction.  It died at
120,084 tokens against a server configured for 131,072, having never once
attempted to compact.  Why did the safety mechanism never fire?

**Verdict.** Because it fired on a declared number rather than a measured one,
and the declared number was 262,144.  Compaction was scheduled for a point the
server would reject 100,000 tokens earlier.  It was not late.  It was
unreachable.

## How the client came to believe 262,144

The configuration file set the context window as a bare key on the model entry.
The client reads it one level deeper, under the entry's generation-config object.

A key at the wrong nesting level is not an error.  It is not a warning either,
and it produces no log line.  It is simply a key nobody reads, sitting next to
keys everybody reads, in a file that validates.

With nothing found, the client fell back to inferring a limit from the model
identifier by pattern.  The identifier missed the specific pattern that would
have matched its family, because the version number in the served name has no
decimal point and the pattern expects one.  It fell through to a generic prefix
rule worth 262,144.

Two independent mechanisms, each individually reasonable, composing into a wrong
answer with no diagnostic anywhere:

| | value |
|---|---|
| server `n_ctx` | 131,072 |
| client's belief | 262,144 |
| auto-compaction threshold | 222,822 |
| where the session actually died | 120,084 |

**All six configured providers had the key in the same wrong place.**  It was
copied, which is what a working-looking configuration invites.

## The escape hatches were also gated on the wrong number

Once a session is past the point of compacting, the manual route matters.  The
model-based compressor requires roughly 20,000 tokens of headroom to summarise
into, so at 120,084 of 131,072 it was already impossible.  It ran for seven
minutes and returned a total token count of exactly 131,072, truncated
mid-summary, having spent the budget it was checking for.

The rule-based compressor, which makes no model call at all, took the same
session from 115,441 to 91,758 tokens in about fourteen milliseconds.

Two further details, both worth carrying:

- **Commands typed during a turn are queued, not executed.**  The escape hatch
  waits behind exactly the turn that is consuming the context.
- **A setting marked as not requiring a restart may still not reach a running
  process.**  That flag suppressed the restart *prompt*; the file watcher behind
  it only notified an unrelated subsystem.  The edit was correct, saved, and
  inert until the client was restarted.

There is a corollary at the other end of the range.  Below roughly 33,000
tokens the threshold ladder degenerates, and automatic compaction cannot succeed
at all.  A limit that is too small fails as silently as one that is too large.

## The same class again, from a hardware migration

Five days later, the always-on tier moved to a different machine.  One provider
entry still declared 98,304 tokens.  The endpoint it now pointed at serves
32,768.  The declaration was correct when it named the old machine; the cutover
changed the server and nobody re-checked the client.

This is worse than a plain mismatch, and the mechanism is the same as the first
case.  The compaction service reads the declared window to decide whether a
payload will fit, and falls back to a larger model when it will not.  **A guard
that trusts a declared number is a guard that waves oversized payloads through
whenever the declaration is generous.**

The honest scope of the damage is smaller than that sounds, and the reason is
worth stating rather than eliding: no compaction model was configured, so
compaction ran on the main model, not this one.  The over-declared provider was
only serving prompt suggestions and speculative execution, both small payloads.
Nothing had failed yet.  It would have failed on the first larger thing routed
there.

The first write-up of this said the mismatch would break compaction.  That was
wrong, and correcting it is part of the finding: the fault was real, the
consequence was not yet.

## The fix, in both cases, is to derive rather than declare

The script that enables that provider now queries the server's own properties
endpoint and asserts that the declared window equals the served `n_ctx`,
aborting on mismatch.  The value is still written into the configuration,
because the client insists on having one, but it can no longer disagree with
reality without someone being told.

The superseded version of that script was retired rather than left in place.  It
still named a host that no longer exists, and its revert path had no preflight
check at all, so it would have happily stripped a working configuration while
talking to a dead machine.

## A third variant: configuration that silently wins

The mirror image showed up in the same period.  A tool warned on every start
that a feature was enabled without its prerequisite, despite the global setting
having that feature switched off.

The cause was a workspace-level settings file, containing exactly one key,
overriding the global.  A sweep found two more of them in sibling directories.
None of the three had any other content; each had presumably been created once,
for one session, and then persisted.

A key at the wrong depth is silently ignored.  A key at the wrong *layer* is
silently obeyed.  Both fail without an error, and neither is visible from the
file you are looking at.

## What generalises

- A limit that governs safety must be read from the thing it protects.  Ask the
  server; do not restate its configuration in a client.
- Where you must restate it, assert equality at startup and refuse to run on
  mismatch.  A declaration nobody checks is a comment with consequences.
- Inferring a capability from a name is a parser applied to a marketing string.
  It will be wrong the first time a naming convention changes, and it will be
  wrong quietly.
- A migration invalidates every recorded fact that described the old host.
  Endpoint constants are the obvious ones; declared limits are not, and they are
  the dangerous half.
- When a mechanism fails to fire, check whether it *could* have fired.  The
  threshold sat 90,000 tokens beyond the server's ceiling, a rule that no input
  could ever satisfy, which is the same failure class as
  [note 09](09-when-the-harness-scores-itself.md)'s harness that could only ever
  return zero.
