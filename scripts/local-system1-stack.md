# Local System-1 / decision-model stack (this box) — inventory + restart runbook

Inventory date: 2026-10-23. All components idle/unloaded since 2026-10-23 16:xx (unloaded
by user request to free ~7.8 GB VRAM for Strata multi-slot). This file is the single
owner of these facts; `~/.dsh/AGENTS.md` carries only a pointer.

## What exists (name → what → where → how to start)

| name | what | where | served by |
|---|---|---|---|
| `qwen3-8b` | Qwen3-8B-Q4_K_M in **--embeddings --pooling last** mode (the CLM backbone/gate), :8091, ctx 2048, ~5.8 GB VRAM | `trade-harvest/data/gguf/Qwen3-8B-Q4_K_M.gguf` | `~/.unsloth/llama.cpp/build/bin/llama-server` (build 11505) |
| `qwen3-embed` | Qwen3-Embedding-0.6B-Q8_0 embedder, :8092, ~1.9 GB VRAM | `~/models/Qwen3-Embedding-0.6B-Q8_0.gguf` | same llama-server binary |
| `CLM_v0.1-8B` | contextual linear model heads (noul/gate) on top of :8091 embeddings | checkpoint `projects/clm/checkpoints/CLM_v0.1-8B.pt`, code `projects/clm/src/clm/` | runs on CPU inside Python; torch venv = the ComfyUI venv |
| ollama | idle, NO GPU resident; one model `huihui_ai/qwen3.5-abliterated:4b` (3.3 GB on disk) | system `/usr/local/bin/ollama` (:11434) | `ollama run huihui_ai/qwen3.5-abliterated:4b` |

## Start / stop

- Up:   `llm-playground/scripts/system1-up.sh`   (idempotent; health-checks both ports; logs to /tmp/system1-<port>.log)
- Down: `llm-playground/scripts/system1-down.sh` (kills only the two llama-server processes bound to :8091/:8092)
- Verify: `curl -s 127.0.0.1:8091/health` / `:8092/health`; VRAM via `nvidia-smi --query-compute-apps=pid,used_memory --format=csv`.

## Known use-proven facts (2026-10-23, decision log)

- CLM noul head over :8091 embeddings for semantic triage ("CSS-demo-worthy"): **AUC 0.973**
  (acc 145/156 at threshold 0.891 — NOT 0.5). Probe: `reels-digest/scripts/clm_triage.py`.
- Market gate (trade-harvest): AUC 0.52 = dead for that task. Semantic tasks = CLM's home turf.
- While :8091+:8092 are up, Strata's expert cache should stay flexed if other GPU work needs
  room (`curl -sX POST 127.0.0.1:8080/v1/vram -d '{"reserve_mib":9000}'`), else normal.

## Do NOT confuse with

- Strata engine (:8080, serves the agent itself) and strata-vision sidecar — user-managed, never kill.
- Local ComfyUI (:8188) — user-managed, never kill.
- Old park/resume scripts for the pre-Strata llama-server (:57501) — superseded, do not use.
