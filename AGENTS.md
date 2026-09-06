# Agent rules for llm-playground

This repo is `oem-agent`'s external storage and playground on GitHub. These rules bind every session that reads from or writes to it.

## Approved uses (in priority order)

1. **Ops script vault** — startup, update, and runner scripts that encode hard-won machine configuration; the "so I don't lose it" archive (see `scripts/`).
2. **Machine-state inventories** — manifests that allow rebuilding or recovering a setup from scratch (custom nodes, models, flags) in `inventory/`.
3. **Backlog / experiment tracker** — durable wishlist of external repos & tools to try, each with status and how it fits the standing goal (see `backlog/`, whose README holds the goal statement). This is where "things I want to try" persist across sessions.
4. **Gists / snippets / memory overflow** — small reusable code and notes; agent memory that is worth keeping durably beyond the local decision log. `notes/`.
5. **Standalone mini-projects** — self-contained source experiments. `projects/`.
6. **Push/pull scratch space** — work artifacts when there is no other sensible place on the local machine.

## Hard rules

- **NO SECRETS.** Never commit tokens, API keys, passwords, private endpoints, or personal data. Before any push: scan staged files for `api[_-]?key`, `secret`, `password`, `bearer`, `github_pat_`, `ghp_`, `sk-…`, private-key blocks. If an archived script contains one, redact it to an environment-variable placeholder and note the variable name in `scripts/README.md`.
- **NO ADULT/NSFW CONTENT.** This is a public repo: no adult material of any kind — not prompts or scene text, not images, not character/name pools referencing real people in sexual contexts. Such material stays on local disk only. When archiving from a local project, archive the *mechanism and format* (scripts, grammar specs), never the content (user rule, 2026-09-06).
- **NO binaries or compiled artifacts** (`.so`, `.pyd`, `.exe`, wheels), **no video**, **no large images**. Text + source + occasional small images only. Keep single files under ~1 MB; keep the whole repo small (target < 50 MB).
- **Keep it simple.** If a file fits none of the approved uses above or breaks a size rule, it does not belong here — find another place.
- **Provenance.** Every archived artifact records where it came from (machine path + date) — in `scripts/README.md` or the manifest's header.
- **Git discipline.** All operations through `gh-git`; commits as `oem-agent`; one logical change per commit; message style `<area>: <what>`.
- **Parallel sessions.** Other agent sessions may work in this repo at the same time. Reads from the shared checkout are safe; **all writes go through a per-session worktree on its own branch**: `gh-git fetch` → `gh-git exec worktree add ../.worktrees/llm-playground-<sess> -b sess/<sess> origin/main` (`<sess>` = first 8 chars of `$DSH_SESSION_ID`) → edit there, stage explicit paths (**never `git add -A`**), commit with `gh-git exec commit` → back in the shared checkout: `gh-git exec merge --ff-only sess/<sess>` (abort if it would touch files another session has dirty) + `gh-git push` → cleanup: `gh-git exec worktree remove ../.worktrees/llm-playground-<sess>` and `gh-git exec branch -d sess/<sess>`. Before committing anywhere, check `git status` and never stage or commit files you did not create — that is another session's in-flight work (2026-09-06 incident: a parallel session's `git add -A` swept an in-flight backlog file into its commit).

## Layout

```
backlog/     "things I want to try" tracker + the north-star goal it serves
scripts/     ops scripts (startup, update, runners) + index with provenance
inventory/   machine-state manifests (custom nodes, …) — regenerable snapshots
notes/       gists, snippets, durable notes / memory overflow
projects/    standalone mini-projects
```
