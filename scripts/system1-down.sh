#!/usr/bin/env bash
# Stop ONLY the System-1 llama-server pair on :8091/:8092 (never Strata/ComfyUI).
# Inventory: llm-playground/scripts/local-system1-stack.md.
set -u
for port in 8091 8092; do
  pid=$(ss -ltnp 2>/dev/null | grep "127.0.0.1:$port " | grep -oP 'pid=\K[0-9]+' | head -1)
  if [ -n "${pid:-}" ] && readlink "/proc/$pid/exe" | grep -q llama-server; then
    kill "$pid" && echo "stopped :$port (pid $pid)"
  else
    echo ":$port not running (or not llama-server — left alone)"
  fi
done
