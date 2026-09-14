# Harness configuration

The two files here are the sanitised working configuration described in
[note 16](../notes/16-the-approval-gate-that-blocked-its-own-linter.md).  They
are published as a worked example, not as something to copy unchanged.

- `opencode.sanitised.json` is the agent, provider, permission, language server,
  and formatter configuration.  Host names, tailnet addresses, and absolute home
  paths are replaced with placeholders.  No credentials were ever stored in this
  file.
- `AGENTS.md` is the global instruction file injected into every session.  It
  carries the delegation policy, the image inspection policy, and the house
  rules.

Two details are worth reading before adapting either file.

Permission rules resolve last match wins, so the order in each `bash` map is
load bearing: the broad allow first, then the patterns that need approval, then
the patterns that are never allowed.  The explicit allow for the tool path sits
after the ask that would otherwise catch it, which is the fix described in the
note.

Read-only agents carry denies and nothing else.  Adding a wildcard allow
alongside those denies, in the same agent block, stops them taking effect for
delegated child sessions, while still reading as correct in both the file and
the API.  Always confirm a permission change by driving a real session rather
than by inspecting the config.
