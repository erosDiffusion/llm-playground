# llm-playground

My local Qwen3.8-27B writes stuff here — a playground for running a **fully-local LLM coding agent** with scoped GitHub access: it clones this repo, works in it, and pushes commits back under its own identity. No cloud inference anywhere in the loop.

It doubles as the agent's small external storage: ops scripts that must not be lost, machine-state inventories, gists/snippets, and standalone mini-projects. What may (and may not) live here is defined in [AGENTS.md](AGENTS.md) — short version: text + source + small images only; **no secrets, no binaries, no video, no large files**.

## What's inside

```
scripts/     ops scripts vault — ComfyUI startup, custom-node updater, remote runner, flow tester (+ provenance index)
inventory/   machine-state manifests — e.g. the 58-pack custom-nodes inventory with origins & commits
notes/       gists, snippets, durable notes (memory overflow)
projects/    standalone mini-projects (one folder each, own README)
AGENTS.md    the rules that bind the agent's use of this repo
```

## The stack

| Layer | What |
| --- | --- |
| Model | Qwen3.8-27B-GGUF (Q4_K_M), fully on GPU via unsloth `llama-server` — local, single-machine |
| Agent runtime | DeepSeek Harness (DSH) — tool loop, sandbox, session presets; driven through its web GUI |
| GitHub access | Fine-grained PAT scoped to **this repo only** (`Contents: read/write`) |
| Git plumbing | `gh-git` wrapper — injects the token per invocation as an HTTP header (never in URLs, files, or history), enforces a repo allowlist, sets the commit identity |

## Reading the history

- **`oem-agent <oem-agent@erosdiffusion.local>`** — written and pushed by the agent. The email is deliberately unregistered, so these commits render as an unlinked identity instead of my profile.
- **`erosDiffusion`** — human commits.
- Note: the *push event* still attributes to the account that owns the token (the PAT lives on the main account); only the commit author metadata carries the agent identity.

## Security model

1. **GitHub-side scope** — the PAT's repository access lists exactly this repo; it is useless everywhere else and revocable at any time (*Settings → Developer settings → Fine-grained tokens*).
2. **Agent-side scope** — a separate allowlist in the agent config (`allowed_repos`); the git wrapper refuses any repo not on it, independent of credentials.
3. **No secret leakage** — the token is injected per call as an `Authorization` header; it never lands in URLs, `.git/config`, tracked files, or history.

## Experiment log

- **2026-09-06** — connection test: first end-to-end agent round (clone → write → commit → push); scope and commit identity verified on the remote.
