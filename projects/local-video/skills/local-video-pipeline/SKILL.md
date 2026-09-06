---
name: local-video-pipeline
description: Use when working on the local 8188 video pipeline — park/resume of the agent LLM, aimdo memory control (unload models / node cache), running or debugging test-local-flows.sh and run-local-video-pipeline.sh, klein image-edit or MiniMax-H3 video renders, or triaging OOM/rejection/transport errors from local ComfyUI.
---

# Local video pipeline (8188) runbook

Local ComfyUI v0.34 at `http://127.0.0.1:8188` (user-run — never start/stop it). Agent LLM = Qwen3.8-27B-GGUF via unsloth studio (:8888), holds ~26.8GB of the 32GB RTX 5090. Klein edit needs ~10–15GB VRAM → **park first**; H3 video (~22–27GB) also parks, but has proven to render on CPU when only ~700MiB is free (slow, not fatal).

## Park / resume (the VRAM window)

- Park: `~/.dsh/bin/agent-park.sh` → thin engine up (MiniCPM5 :57600) → unload 27B from studio → flip route to `park-engine/park-thin`. **Studio unload REQUIRES the native path** as `model_path`: `/home/oem/.lmstudio/models/lmstudio-community/Qwen3.8-27B-GGUF` (public id silently no-ops; real kill logs `Unloaded GGUF model:`, no-op logs bare `Unloaded model:`).
- Resume: `~/.dsh/bin/agent-resume.sh` → load 27B first (poll ready) → restore route → stop thin engine LAST.
- **Never call studio unload while you still need to respond** — it kills your next LLM call by design. Real unloads only inside detached work after the final message lands.
- Full detail + root cause: `~/.dsh/AGENTS.md` (Park/Resume protocol) and `~/.dsh/memory/decisions.md`.

## Memory control on 8188 = aimdo API (pack ComfyUI-MemoryVisualization)

| Action | Endpoint |
|---|---|
| status (loaded models, vbar residency, RAM) | `GET /aimdo/vram` |
| immediate unload (409 if executing — safe) | `POST /aimdo/unload_all` |
| models on next queue tick | `POST /free {"unload_models":true}` |
| **models + node cache** (big cleanup) | `POST /free {"unload_models":true,"free_memory":true}` |

**User policy: scripts must NOT auto-call /free.** Memory management is manual — the user clicks the GUI "unload ▾" menu or curls the endpoints above. Never add auto-unload to pipeline scripts.

## Scripts (workspace root)

- `test-local-flows.sh` — standalone, no park/auto-unload. **Submits all selected flows first, then waits in order.** Env: `KLEIN_ONLY=1` / `H3_ONLY=1` / `NO_WAIT=1` (enqueue+exit) / `DRY_RUN=1`; budgets `KLEIN_MAXC/INTV`, `H3_MAXC/INTV`. Report → `work/flow-test-report.md`; exit 1 on any FAIL.
- `~/.dsh/bin/run-local-video-pipeline.sh` — full park→klein→H3→resume chain (no /free calls).
- Preflight yourself before klein: free VRAM via aimdo/studio; H3 can go without it.

## Render files & recipes (API format, `comfyui/local/`)

- `runs/01-klein-edit.json` — Flux2-Klein 9B kv-fp8 reference edit (ReferenceLatent pos+neg, CLIP `qwen_3_8b_fp8mixed` in `text_encoders/`, flux2-vae, 4 steps euler_a cfg 1). Output node 1844.
- `runs/02-h3-video.json` — MiniMax-H3 i2v (`MiniMaxH3Easy` node 2010 + media_1 ref), LightX2V turbo LoRA @0.75, LCM 4 steps, 1344×768 5s 24fps, audio out. Output node 2005 (SaveVideo). SaveVideo `format` is COMFY_DYNAMICCOMBO_V3 — dotted `"format.codec"` key is valid; "auto" everywhere is the safe setting.
- Both proven: klein 3× + H3 2× successes in `/history` (incl. one CPU-only H3 at 23:53 → `output/video-test/02-rich-hero_00001_.mp4`).

## Protocol facts (v0.34)

- `POST /prompt` body must be **wrapped**: `{"client_id":"...","prompt":<api-format>}` — raw API dict is rejected with "no_prompt".
- Poll `GET /history/<prompt_id>`; outputs via `GET /view?filename=..&subfolder=..&type=output`.
- Error triage: **transport** (curl rc≠0 / non-JSON — server may have accepted the job! check queue before resubmitting) vs **rejected** (`node_errors` in response = real graph/wiring problem) vs **job error** (history `status.messages` → `execution_error` with node_id + exception). OOM while the 27B is resident = expected for klein, not a graph bug.

## Remote box (192.168.1.34:9000) — Z-Image Turbo

Recipe + procedure in workspace AGENTS.md; without MCP tools use `comfy-remote.sh` (curl wrapper: submit → poll → download). Fresh seed per shot; storyboard = simple text-only workflow, reroll with new seed before changing wording.
