# Remote box (192.168.1.34): memory orchestration protocol

Verified 2026-09-06 by direct testing against the live box. This is the operating
protocol for using the render box without OOM or VRAM races.

## The two subsystems that do NOT know about each other

| Subsystem | Port | Memory control |
|---|---|---|
| ComfyUI v0.34 (separate process) | :8188 | `POST /free {"unload_models":true}` + verify via `/system_stats` |
| unsloth studio (separate process) | :8888 | `POST /api/inference/unload` (LLM), `/api/inference/images/unload`, `/api/inference/video/unload` |

**Neither sees the other's allocations.** Two models from two subsystems will happily
hold VRAM/RAM at the same time. The agent orchestrates: free one before using the other.

## What DOES auto-evict (verified)

Unsloth studio has ONE active-model manager spanning all its subsystems — loading any
model evicts whatever was active, in either direction:

- LLM→diffusion: loaded `FLUX.2-klein-9B` (images subsystem) while gemma-E4B was
  active → gemma evicted within 5 s, klein on cuda.
- diffusion→LLM: reloaded gemma → klein evicted, gemma active again.

So switching WITHIN unsloth (LLM ↔ image ↔ video models) needs no manual eviction.
Switching BETWEEN unsloth and ComfyUI always needs the protocol below.

## The protocol (enforced by `remote-gpu`)

```
before ComfyUI work:  remote-gpu ensure-free          # frees both, verifies, exits 0 when clean
run workflow ...      comfy-remote.sh run <wf.json>
after:                remote-gpu free-comfy           # don't leave diffusion weights resident

before unsloth work:  remote-gpu ensure-free
                      remote-gpu load-llm unsloth/gemma-4-E4B-it-GGUF   (or load-image ...)
call LLM ...
```

`remote-gpu status` shows the full picture at any time: ComfyUI up/down, VRAM free/total,
RAM free/total, active unsloth model, images-subsystem state.

## Per-install differences (do NOT assume one install's templates fit the other)

| | LOCAL box (this machine) | REMOTE box 192.168.1.34 |
|---|---|---|
| GPU | RTX 5090, 32GB | **RTX 3080, 10GB** |
| RAM | ~91GiB | ~31GiB |
| ComfyUI port | :8188 (localhost) | :8188 (192.168.1.34) — **always include the host in URLs** |
| Image models | Flux2-Klein 9B, MiniMax-H3 stack, LTX video | `z_image_turbo_bf16.safetensors` + CLIP `qwen_3_4b.safetensors` (type **lumina2**) + VAE `ae.safetensors`; klein-9B lives in UNSTLOTH's images subsystem, not ComfyUI |
| Memory node (aimdo) | **yes** (`/aimdo/vram`, `/aimdo/unload_all`) | **no** (all 404; also no ComfyUI-Manager → can't install via API) |
| unsloth | :8888 localhost, Qwen3.8-27B serves the agent | :8888 on 192.168.1.34, gemma-E4B (fast) / Qwen3.8-27B (~3.5 tok/s) |

**Rule:** before running any workflow template against a target install, probe it:
`curl http://<host>:<port>/object_info/<Node>` and check the model lists
(`UNETLoader`/`CLIPLoader`/`VAELoader`). Templates are per-install.

## Unsloth studio API map (remote, 380 endpoints — the useful ones)

- LLM: `POST /api/inference/load|unload` body `{"model_path":"unsloth/<name>"}`;
  `GET /api/inference/status`; v1 chat at `/v1/chat/completions`
- Images: `POST /api/inference/images/load` body
  `{"model_path":"<repo>","gguf_filename":"<file>.gguf","model_kind":"gguf"}` (+ optional
  `cpu_offload`, `memory_mode`); `/images/status|unload|generate|generate-progress`
- Video: same shape under `/api/inference/video/*`
- Planning: `POST /api/inference/estimate-memory` — prices a prospective load from GGUF
  headers before anything is allocated (safe to call anytime)
- Discovery: `GET /api/hub/gguf-variants?repo_id=<urlencoded repo>` → which `.gguf` files
  are downloaded; `GET /api/models/list`; `GET /openapi.json` for the full surface
- Auth: `GET/POST /api/auth/api-keys`, `DELETE /api/auth/api-keys/{key_id}`.
  Keyless mode is a server setting (studio UI), not an API call.

## Known limits on this hardware (10GB VRAM)

- Qwen3.8-27B: ~7GB resident, ~3.5 tok/s, **context capped at 8192** by the studio's
  VRAM heuristics (not overridable via API).
- gemma-E4B: ~0.7 s/80 tokens, context capped at 43008 (native 131k).
- Both models default to thinking mode → empty `content`; send per-request
  `"chat_template_kwargs":{"enable_thinking":false}` for clean answers.
- klein-9B Q4_K_M = 5.5GB, loads with most weights in RAM + partial cuda (device:cuda).
