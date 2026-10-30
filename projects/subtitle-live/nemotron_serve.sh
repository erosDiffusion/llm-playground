#!/usr/bin/env bash
# Serve Nemotron 3.5 Transcribe NVFP4 (models/nemotron) on :8097 via vLLM.
#
# ⚠ READ FIRST:
#  - Needs ~27 GB VRAM (gpu-memory-utilization 0.85 of 32 GB). The Strata
#    engine (the agent) MUST be stopped first — this agent session goes
#    offline while it runs. There is no flex window big enough.
#  - Cue mode never needs this: Prime already provides text. Use it only in
#    AUDIO mode (no subtitles on the title): one call = ASR + translation
#    ("Please translate the given speech to English.").
#
# One-time env install (first run only, ~8 GB):  ./nemotron_serve.sh --install
# Then:                                          ./nemotron_serve.sh
set -e
cd "$(dirname "$0")"
VENV=models/nemotron/.venv

if [ "$1" = "--install" ]; then
  python3 -m venv "$VENV" 2>/dev/null || uv venv "$VENV" --python 3.12
  uv pip install -p "$VENV/bin/python" "vllm==0.32.*" openai
  uv pip install -p "$VENV/bin/python" nemo-toolkit \
    || echo "NOTE: if nemo-toolkit wheel fails, follow the NeMo Speech install guide (source install)"
  echo "env ready: $VENV"
  exit 0
fi

if pgrep -f "strata" >/dev/null && curl -sm2 http://127.0.0.1:8080/health >/dev/null; then
  echo "ERROR: Strata engine is serving on :8080 — stop it first (agent goes offline)." >&2
  exit 1
fi

export VLLM_PLUGINS=nemo_speechlm
export VLLM_MAX_AUDIO_DECODE_DURATION_S=3600
export VLLM_MAX_AUDIO_CLIP_FILESIZE_MB=180
export VLLM_USE_V2_MODEL_RUNNER=0
export VLLM_DISABLED_KERNELS=FlashInferFP8ScaledMMLinearKernel

exec "$VENV/bin/vllm" serve ./models/nemotron \
  --served-model-name nemotron-transcribe \
  --host 127.0.0.1 --port 8097 \
  --trust-remote-code --dtype bfloat16 --kv-cache-dtype fp8 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 16384 --max-num-batched-tokens 4096 --max-num-seqs 8 \
  --enable-chunked-prefill --no-enable-prefix-caching \
  --use-replayssm --mamba-backend flashinfer --mamba-cache-mode none \
  --mm-processor-cache-gb 0 --no-async-scheduling \
  --limit-mm-per-prompt '{"audio":{"count":1,"length":57600000}}' \
  --speculative-config '{"method":"mtp","num_speculative_tokens":8}' \
  --reasoning-parser nemotron_v3 --trust-request-mm-kwargs
