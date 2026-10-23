#!/usr/bin/env bash
# Bring up the local System-1 stack (qwen3-8b embeddings :8091, qwen3-embed :8092).
# Inventory + facts: llm-playground/scripts/local-system1-stack.md. Idempotent.
set -u
LLAMA=/home/oem/.unsloth/llama.cpp/build/bin/llama-server
up(){ local port=$1; shift
  if ss -ltn | grep -q "127.0.0.1:$port "; then echo ":$port already up"; return 0; fi
  nohup "$LLAMA" "$@" --host 127.0.0.1 --no-webui >"/tmp/system1-$port.log" 2>&1 &
  echo "starting :$port -> log /tmp/system1-$port.log"; }
up 8091 -m /home/oem/Apps/deepseek-workspace/trade-harvest/data/gguf/Qwen3-8B-Q4_K_M.gguf \
   --embeddings --pooling last --port 8091 --alias qwen3-8b --ctx-size 2048 -ngl 99 -b 512 -ub 512
up 8092 -m /home/oem/models/Qwen3-Embedding-0.6B-Q8_0.gguf \
   --embeddings --pooling last --port 8092 --alias qwen3-embed -ngl 99 -c 4096
for i in $(seq 1 30); do
  a=$(curl -s -o /dev/null -w %{http_code} 127.0.0.1:8091/health)
  b=$(curl -s -o /dev/null -w %{http_code} 127.0.0.1:8092/health)
  [ "$a" = 200 ] && [ "$b" = 200 ] && { echo "system1 up (8091+8092 healthy)"; exit 0; }
  sleep 2
done
echo "WARN: health not green after 60s (a=$a b=$b) — check /tmp/system1-*.log"; exit 1
