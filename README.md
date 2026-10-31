# llm-playground

My local agent brain — **qwen3.8-flash-next (IQ3_S MoE) served by the Strata engine** — writes stuff here: a playground for running a **fully-local LLM coding agent** with scoped GitHub access: it clones this repo, works in it, and pushes commits back under its own identity. No cloud inference anywhere in the loop.

It doubles as the agent's small external storage: ops scripts that must not be lost, machine-state inventories, gists/snippets, and standalone mini-projects. What may (and may not) live here is defined in [AGENTS.md](AGENTS.md) — short version: text + source + small images only; **no secrets, no binaries, no video, no large files**.

Parallel-safe write workflow (worktree-per-session + rebase/squash + ff-only landing) is documented in [WORKFLOW.md](WORKFLOW.md).

## What's inside

```
backlog/     "things I want to try" tracker — external repos/tools with status, serving the north-star goal (Blender previs → MiniMax H3, user-driven camera)
scripts/     ops scripts vault — ComfyUI startup, custom-node updater, remote runner, flow tester (+ provenance index)
inventory/   machine-state manifests — e.g. the 58-pack custom-nodes inventory with origins & commits
notes/       gists, snippets, durable notes (memory overflow)
projects/    standalone mini-projects (one folder each, own README)
AGENTS.md    the rules that bind the agent's use of this repo
```

## The stack

| Layer | What |
| --- | --- |
| Model | **qwen3.8-flash-next** (IQ3_S MoE, ~10.8k experts, 262k ctx) served by the **Strata engine** at `:8080` with an elastic expert cache (`--vram-elastic`, flex API `POST /v1/vram`) — local, single-machine. Legacy unsloth `llama-server` (Qwen3.8-27B-Q4_K_M, :57501) retired, down — probe 2026-10-31 |
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
