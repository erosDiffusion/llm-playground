# Local engines inventory (this box: RTX 5090 32GB, 91GiB RAM)

Survey doc, probed **2026-10-31** from a DSH session (every number below carries its probe;
re-run the probes before acting on a stale fact). One owner per fact: versions, install
paths, ports, launch recipes live HERE; VRAM-flex mechanics stay in
`scripts/strata-vram-flex.md`; System-1 embedding stack detail in
`scripts/local-system1-stack.md`.

## Re-probe block (run this to refresh every status cell)

```bash
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
free -h | head -2
ss -ltn | grep -E "8080|11434|11987|8188|8091|8092|57501|1234"
curl -m2 -s 127.0.0.1:8080/health && echo   # Strata
curl -m2 -s 127.0.0.1:11434 && echo         # Ollama
ollama ps                                     # loaded models (empty = idle)
cat /home/oem/Progetti/ComfyUI/comfyui_version.py   # ComfyUI version
git -C ~/Apps/Strata describe --tags          # Strata repo tag
ollama --version; ~/Apps/vllm/.venv/bin/python -c "import vllm;print(vllm.__version__)"
~/Apps/sglang2/venv/bin/python -c "import sglang;print(sglang.__version__)"
```

## Quick table (probe 2026-10-31)

| Engine | Version | Path | Port | State at probe | Idle cost | Disk |
|---|---|---|---|---|---|---|
| Strata (serves the agent) | repo v0.2.8 / engine 0.1.54 | `~/Apps/Strata` | 8080 | RUNNING | ~29.6 GB VRAM | ~repo |
| Ollama | 0.33.1 | `/usr/local/bin/ollama` | 11434 | RUNNING, no model loaded | 19 MB RAM, 0 VRAM | model 3.3 GB |
| llama.cpp (unsloth build) | llama-server binary | `~/.unsloth/llama.cpp/build/bin` | 8091/8092 (System-1) | not running | 0 | build tree |
| SGLang | 0.5.19 | `~/Apps/sglang2/venv` | (none chosen) | not running, eval | 0 | 9.0 GB |
| vLLM | 0.28.0 | `~/Apps/vllm/.venv` | (none chosen) | not running, eval | 0 | 7.7 GB |
| LM Studio | 0.4.23 | AppImage `~/Apps/` + `~/.lmstudio` (8.1 GB) | 1234 (default) | not running | 0 | 8.1 GB + AppImage |
| ComfyUI (diffusion) | 0.43.0 | `/home/oem/Progetti/ComfyUI` | 8188 | DOWN at probe | 0 | — |
| ~~NInfer~~ | removed | traces: `~/.dsh/ninfer` (fixtures+patches), vault `scripts/` kits | — | GONE | 0 | — |

Non-engine neighbors on ports: 3080 DSH web GUI, 8099 ti4 game server, 8891 h3-widget
comfy-relay (→ remote 8188), 3337 backlog board.

## Per-engine runbook

### 1. Strata — the agent's own engine (USER-MANAGED: never start/stop/kill)
- Serves me: qwen3.8-flash-next IQ3_S MoE, `--slots 2`, `--vram-elastic`; strata-vision sidecar ≈1.7 GB.
- VRAM when up: ≈29.6 GB (probes 2026-10-31) → only ~2.3 GB free.
- To make room for any other engine: flex the expert cache `POST :8080/v1/vram {"reserve_mib":N}`
  (full protocol + honest numbers in `scripts/strata-vram-flex.md`; reclaim `null` after).

### 2. Ollama — systemd service (boot-enabled)
- Unit `/etc/systemd/system/ollama.service`: bare `ollama serve`, no preload, no `OLLAMA_*` env.
- Built-in lifecycle: lazy load on first request, auto-**unload after 5 min idle** (`keep_alive` default;
  knob = `OLLAMA_KEEP_ALIVE` in the unit; preload pattern = `ExecStartPost` + keep_alive=-1 — NOT used here).
- Only model on disk: `huihui_ai/qwen3.5-abliterated:4b` (3.3 GB).
- Idle cost (probe): RSS 18–19 MB, 0 VRAM, CPU ~0.
- GOTCHA: 3.3 GB model > ~2.3 GB free while Strata is full → request will CPU-offload or fail.
  Flex Strata first (reserve ≈4–6 GB) before loading it.
- Treat as user-managed: probe freely; don't restart the service without asking.

### 3. llama.cpp (unsloth build) — System-1 embeddings server
- Binary `~/.unsloth/llama.cpp/build/bin/llama-server` (also retired 27B path — not the usual engine, never assume :57501 up).
- Start/stop ONLY via `scripts/system1-up.sh` / `system1-down.sh` (idempotent;
  :8091 Qwen3-8B-Q4_K_M embeddings ≈6.3 GB, :8092 Qwen3-Embedding-0.6B-Q8_0).
- Check before down — shared resource, a parallel session may use it for CLM work.
  Full stack + proven metrics: `scripts/local-system1-stack.md`.

### 4. SGLang 0.5.19 — installed, never served on this box (eval)
- `~/Apps/sglang2/venv` (9.0 GB). Launch shape: `venv/bin/python -m sglang.launch_server --model-path <hf-id-or-path> --port <p>` (+`--mem-fraction-static` to cap).
- venv python also has `killall_sglang` helper in `venv/bin/`.
- NOT verified end-to-end here — treat first real run as experimental (model must come from HF cache; do not download big weights without asking).

### 5. vLLM 0.28.0 — installed, never served on this box (eval)
- `~/Apps/vllm/.venv` (7.7 GB). Launch shape: `.venv/bin/vllm serve <model> --gpu-memory-utilization <0..1> --port <p>`.
- Same caveat: untested on this box, weights downloads need user consent.

### 6. LM Studio 0.4.23 — GUI + `lms` CLI, not running
- AppImage `~/Apps/LM-Studio-0.4.23-1-linux-x64.AppImage`; data `~/.lmstudio` (8.1 GB; `bin/lms` works).
- One GGUF cached: `Qwen3.8-27B-DFlash2-Q4_K_M` (~1.1 GB dir — verify size before loading).
- `lms server start` → :1234 (headless option exists, GUI not required).
- 27B Q4 ≈ 17 GB+ → needs Strata flexed hard, same window logic as klein/H3.

### 7. ComfyUI 0.43.0 (diffusion, not an LLM) — USER-RUN: never start/stop
- `/home/oem/Progetti/ComfyUI`, :8188; DOWN at 2026-10-31 probe. Queueing via HTTP when up is fine.
- aimdo memory API + local flows: skill `local-video-pipeline`; never auto-call `/free` (user policy).

## VRAM decision ladder (probe-based, 2026-10-31)

- Strata full (default): ~2.3 GB free → only Ollama-idle, tiny models (≤~1.5 GB e.g. 0.6B embeddings) fit.
- Flex `{"reserve_mib":6144}` → Ollama qwen3.5-abliterated:4b (3.3 GB) or System-1 0.6B fits.
- Flex `{"reserve_mib":~14336}` → System-1 Qwen3-8B (6.3 GB) + 0.6B together.
- Flex `{"reserve_mib":22016}` (~19.4 GB free, proven 2026-10-31) → vLLM/SGLang small–mid models, LM Studio 27B (tight), klein class.
- H3-class (22–27 GB): flex to floor or CPU-slow; Z-Image/Flux-class image gen → remote box instead.
- Reclaim `{"reserve_mib":null}` right after the other engine exits. Never flex while that engine is mid-request on Strata (`ModelBusy` → retry at tool boundary).

## Provenance

Survey written 2026-10-31 by a DSH agent session (id 4fd2a5e4) from live probes listed above;
versions re-read from binaries/venvs, not from notes. NInfer confirmed absent from disk except
archaeology paths. LM-Studio/vLLM/SGLang existence was NOT in any prior note — this doc is their
only inventory entry.
