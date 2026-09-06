# WORKFLOW — parallel-safe git policy (machine-discoverable)

Canonical workflow for any agent/harness session writing to this repo.

## Goals

- Parallel sessions never conflict in-place.
- Work is additive and based on latest `main`.
- History stays clean: one logical change per commit.

## Mandatory rules

1. Never write directly in the shared checkout when other sessions may run.
2. Create one dedicated worktree + branch per session.
3. Rebase session branch onto latest `origin/main` (no merge commits in session branch).
4. Squash incremental task commits into one clean logical commit before landing.
5. Land to `main` using fast-forward only.
6. Stage explicit paths only (never `git add -A`).

## Standard command flow (`gh-git`)

```bash
gh-git fetch
gh-git exec worktree add ../.worktrees/llm-playground-<sess> -b sess/<sess> origin/main

# ... edit in the worktree ...
gh-git exec add <explicit-paths>
gh-git exec commit -m "<area>: <what>"

# if main moved
gh-git fetch
gh-git exec rebase origin/main

# optional: squash N commits into one before landing
gh-git exec reset --soft HEAD~<N-1>
gh-git exec commit -m "<area>: <what>"

# back in shared checkout
gh-git exec merge --ff-only sess/<sess>
gh-git push

# cleanup
gh-git exec worktree remove ../.worktrees/llm-playground-<sess>
gh-git exec branch -d sess/<sess>
```

`<sess>` = first 8 chars of `$DSH_SESSION_ID`.

## Safety checks before push

- `git status --short` shows only intended files.
- No secrets scan hits in staged diff.
- Commit message follows `<area>: <what>`.

## Source of truth

- This file is the operational quick reference.
- Policy authority remains `AGENTS.md`.