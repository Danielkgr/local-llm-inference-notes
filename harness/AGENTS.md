# Global OpenCode Rules

## Delegation-first repository discovery

This section applies to interactive primary work agents such as `build`, `plan`, `vibe`, and `scout`. If you are `explore`, `title`, `summary`, `compaction`, or another leaf child agent, do not apply this section recursively.

- Preserve the primary model's context for reasoning, decisions, implementation, and final verification.
- Strong default: when a request spans multiple subsystems or asks for an architecture map, inventory, audit, or other broad understanding, make the first repository-discovery action a `task` delegation to `explore`. Do this before direct `read`, `glob`, `grep`, or `list` calls and before discovery-oriented shell commands such as `find`, `ls`, `rg`, `grep`, or `sed`.
- Do not replace delegation with one large shell command that dumps a repository tree or many files into the primary context. For narrower uncertain work, more than roughly 3-5 discovery calls is another useful signal to delegate, but this is a heuristic, not a quota.
- Give each Explore task a bounded question, directory or subsystem scope, read-only boundary, and requested evidence: relevant paths, symbols or line references, concrete findings, and unresolved questions.
- When a request names three or more independent areas, do not combine them into one oversized child task. Split the areas into 2-4 focused Explore tasks and issue them together in one tool turn when parallel tool calls are available. Prefer one focused task only when the evidence is tightly coupled.
- Use child results instead of repeating their exploration. Across one parent turn, direct verification should usually require no more than 1-3 targeted `read`, `grep`, or `glob` calls in total; this is a context-preservation heuristic, not a hard prohibition.
- If a child reports a step limit, partial result, or unresolved multi-file gap, delegate one focused follow-up Explore task. Do not switch back to a bulk parent pass or describe a large set of parent calls as "a few targeted reads."
- Direct exploration is appropriate for a known file, a small localized task, quick verification, or when delegation overhead would exceed the work.
- If delegation is unavailable or fails, continue directly and report the fallback. Never delegate to evade permissions, safety boundaries, or responsibility for the final result.

## Screenshot and image inspection

- When an image attachment notice includes `image_id`, call `vision_inspect` with that exact ID and the specific visual question before describing the screenshot or implementing a fix based on it. Multiple IDs can be inspected together.
- If an old screenshot no longer has a visible ID after compaction, call `vision_inspect` with just `question` to recover the latest stored image message in this session.
- For images on disk, call `vision_inspect` with `file_paths`. A pasted attachment filename is not necessarily a local path. The tool forwards the actual pixels to the local Model-H `vision` agent and returns its observations.
- Ordinary `task` delegation does not forward pasted image attachments. Use `vision_inspect` for attachment handoff. Use `task` with `vision` only for explicit real file paths.
- If vision fails, report the failure and retry when appropriate. Do not infer image contents from filenames, source code, or old handovers saying screenshots are unsupported. Do not ask the user to transcribe a screenshot before trying the vision tool.
- The `vision` agent is a leaf: never apply repository-discovery delegation recursively.

## House rules

These apply to every session on this machine, in every repository, and to primary and child agents alike.

- Write Australian English in comments, documentation, commit messages, and prose output.
- Do not use em dashes or en dashes in prose or documentation.  Use a comma, a colon, or a full stop instead.  Code, identifiers, string literals, and fenced blocks are exempt.
- Put two spaces after every full stop in prose and documentation.
- Use Oxford commas, and prefer active voice.
- Keep diffs small and reviewable.  Make one coherent change at a time, and split unrelated work into separate edits rather than bundling it into one large patch.
- Tests come before refactors.  Before moving or restructuring code, confirm a test already covers the behaviour.  If none exists, write one first, confirm it passes against the unchanged code, and only then refactor.
- After editing, run the repository's own lint and test commands, then report the exact command line and its result.  Do not describe work as complete or verified without that evidence.
- Report what you find, not what you assume.  Mark anything you could not verify as UNVERIFIED rather than presenting it as fact.
- Never add AI attribution to anything that may become public.  No `Co-Authored-By` trailers, no assistant or tool names in commit messages, and no generated-by notices.
