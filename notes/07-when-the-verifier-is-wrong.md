# Worktree detection, backup omissions, and stale checks

An audit found that two scripts used a directory check to detect Git
repositories.  It excluded worktrees, whose `.git` entry is a file.  The
scripts then omitted the production build from backup and update reporting.

```sh
if [ -d "$dir/.git" ]; then
```

**A git worktree's `.git` is a file, not a directory.**  Sixty-one bytes,
pointing at the real git directory elsewhere.  Every `git` command works
normally inside it.  This test returns false.

That matters here because build bumps are done as worktrees, so the tree that
is actually in production is precisely the one this check cannot see.

## Failure 1: a backup that exited zero and omitted production

The backup script reported DONE and did not contain the inference binary the
machine actually runs.  Its include list was hardcoded and had gone stale: it
archived the old build tree and not the current one, which is the tree the
service launcher executes.

It also omitted three of five virtual environments, and the dependency manifest
loop had the same gap.  A long-dead entry produced a permanent skip warning on
every run, which had trained the eye to ignore skip warnings entirely.

Separately, the off-site mirror script verified one archive by checksum while
its report read as though the whole run had been attested.

The fix lists the archive members and checks for the serving binary.  Exit
status alone did not establish that the required files were included.

The repairs were structural rather than specific: glob patterns instead of a
hardcoded list, so the next build bump or new environment is picked up without
editing the script, and every include line printed so an omission is visible in
the log rather than inferred from its absence.

## Failure 2: the update checker understated the version by 454 commits

The update checker reported the old build as installed and 458 commits behind,
recommending an upgrade.  Production was running the newer build, four commits
behind.

Same worktree test, in two functions.  The check saw the worktree as absent and
silently fell back to the superseded main tree.

The script's footer already recorded the newer build as adopted.  The footer
was correct, but the automatic check read the wrong tree.

The fix does not test for the tree by name.  It derives it from the service
launcher's exec line, so the check now reads the same source of truth the
machine does, and the retained rollback tree prints on its own labelled row
where it can never again pose as current.

## Failure 3: a recorded fact that was wrong when it was written

A stored note incorrectly said that the image pipeline had no GPU-memory
release mechanism and that raising a timeout would break generation.  The
release hook had already existed for three weeks.

The release hook existed.  It was a plugin inside the image application's
plugin directory, which sits in that project's `.gitignore`, so it was
invisible to status, log, and every tracked-file search.  The note had looked
for a wrapper script and a service hook, found neither, and concluded the
mechanism was absent.  It therefore recommended an unnecessary implementation.

**A gitignored plugin directory is a real extension point that version control
will not show you.**  Grep it explicitly.

The correction was made by exercising the behaviour rather than reading more
code: load a model, trigger a render, watch memory actually fall and the render
complete.

## A fourth, different in kind

An environment was stripped and its apparent size fell by nearly 4 GiB, while
free disk did not move.  The package manager hardlinks its cache into the
environment, and deleting one link frees nothing while the other survives.

`du` reports apparent size.  Link count reports reclaimable space:

```sh
find <path> -name "*.so*" -size +50M -printf "%n links %f\n"
```

One link means real reclaim.  Two means hardlinked, and deleting frees nothing.

Checking that before pruning also revealed which cached entries were still
referenced by a different environment, so a generic prune would have destroyed
something in use.

## Scope

These checks now follow the runtime selected by the launcher and inspect
archive contents.  Neither a successful exit nor an old include list is
sufficient evidence that the current serving binary is recoverable.
