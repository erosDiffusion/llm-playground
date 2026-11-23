# Basalt upgrade kit (vault copy)

Deterministic upgrades for the **Basalt engine** (`~/Apps/Basalt/basalt`, origin
github.com/jesdga95/basalt, supervisor :8090) — the sibling of the Strata kit in [`strata/`](../strata/README.md).
Full protocol: [`../dsh-strata-upgrade-protocol.md`](../dsh-strata-upgrade-protocol.md) **§D**.

| File | Role | Live copy |
|---|---|---|
| `basalt-upgrade-check.sh` | READ-ONLY preflight: newest remote tag (fetches only the target tag ref), live-engine flag compat via `git grep` in the tag, serve-layout + model-arch presence, tracked-tree cleanliness, release-archive prerequisites (driver ≥ R580, libcudart 13, requirements.txt drift) | `~/.dsh/bin/` |
| `swap-basalt.sh` | the swap itself — refuses without `USER_OK=1`; MUST run detached (the agent brain dies with it, ~3–5 min incl. the page-locked expert load). Saves `bin/*` → `bin/basalt.previous/`, optionally stages a release archive's `bin/*`, path-anchored kill (can never hit Strata), relaunch via `scripts/basalt-serve.sh <VARIANT>` (default `262k2v`), verifies `/health loaded:true`, prints the one-line rollback | `~/.dsh/bin/` |

Provenance: authored 2026-11-23 against tag v0.5.5 (newest then: v0.5.6, pending on this box).
Preflight green that day: 9/9 live engine flags present in v0.5.6, serve layout + `qwen4exp` arch present,
tracked tree clean, archive route ready (driver 595, CUDA 13.2, requirements.txt unchanged between tags).
Untracked local additions that must survive (launcher + variants live here, never in tracked files):
`configs/`, `scripts/basalt-serve.sh` (+ bench/free/load scripts), `OPS.md`, `basalt_config.json`,
plus gitignored `bin/` and `.venv/`.
