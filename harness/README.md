# Harness configuration

This is a historical example, not the current configuration on either host.
Provider routes, models, context, permissions, and client behaviour have since
changed.  The observed setup is described in [CURRENT.md](../CURRENT.md).

The two files here are the sanitised configuration described in [note
16](../notes/16-the-approval-gate-that-blocked-its-own-linter.md).  They are
published as a worked example, not as something to copy unchanged.

- `opencode.sanitised.json` is the agent, provider, permission, language server,
  and formatter configuration.  Host names, tailnet addresses, absolute home
  paths, and model identifiers are replaced with placeholders.  A model
  placeholder such as `Model-E-27B (Q5_K_M)` keeps the size, the quantisation,
  and any role, and drops the name, as the notes do.  No credentials were ever
  stored in this file.
- `AGENTS.md` is the global instruction file injected into every session.  It
  carries the delegation policy, the image inspection policy, and the house
  rules.

Two details matter when reading this example.

Permission rules resolve last match wins, so the order in each `bash` map is
load bearing: the broad allow first, then the patterns that need approval, then
the patterns that are never allowed.  The explicit allow for the tool path sits
after the ask that would otherwise catch it, which is the fix described in the
note.

In the client version tested for the note, read-only agents carried denies and
nothing else.  Adding a wildcard allow alongside those denies, in the same
agent block, stops them taking effect for delegated child sessions, while still
reading as correct in both the file and the API.  This is recorded
version-specific behaviour.  It is not a guarantee about later clients.  Any
new permission test on Box or Strix needs its own model-test authorisation.
