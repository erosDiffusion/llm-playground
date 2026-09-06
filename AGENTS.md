# Agent rules for llm-playground

This repo is `oem-agent`'s external storage and playground on GitHub. These rules bind every session that reads from or writes to it.

## Approved uses (in priority order)

1. **Ops script vault** — startup, update, and runner scripts that encode hard-won machine configuration; the "so I don't lose it" archive (see `scripts/`).
2. **Machine-state inventories** — manifests that allow rebuilding or recovering a setup from scratch (custom nodes, models, flags) in `inventory/`.
3. **Gists / snippets / memory overflow** — small reusable code and notes; agent memory that is worth keeping durably beyond the local decision log. `notes/`.
4. **Standalone mini-projects** — self-contained source experiments. `projects/`.
5. **Push/pull scratch space** — work artifacts when there is no other sensible place on the local machine.

## Hard rules

- **NO SECRETS.** Never commit tokens, API keys, passwords, private endpoints, or personal data. Before any push: scan staged files for `api[_-]?key`, `secret`, `password`, `bearer`, `github_pat_`, `ghp_`, `sk-…`, private-key blocks. If an archived script contains one, redact it to an environment-variable placeholder and note the variable name in `scripts/README.md`.
- **NO binaries or compiled artifacts** (`.so`, `.pyd`, `.exe`, wheels), **no video**, **no large images**. Text + source + occasional small images only. Keep single files under ~1 MB; keep the whole repo small (target < 50 MB).
- **Keep it simple.** If a file fits none of the approved uses above or breaks a size rule, it does not belong here — find another place.
- **Provenance.** Every archived artifact records where it came from (machine path + date) — in `scripts/README.md` or the manifest's header.
- **Git discipline.** All operations through `gh-git`; commits as `oem-agent`; one logical change per commit; message style `<area>: <what>`.

## Layout

```
scripts/     ops scripts (startup, update, runners) + index with provenance
inventory/   machine-state manifests (custom nodes, …) — regenerable snapshots
notes/       gists, snippets, durable notes / memory overflow
projects/    standalone mini-projects
```
