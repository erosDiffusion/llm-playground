#!/usr/bin/env bash
# Projects-panel stop: daemon (pidfile) + subctl + the ASR/MT llama-servers
# THIS project starts. Patterns anchored to this project's model paths so
# user-managed llama-server instances (e.g. legacy :57501) are never touched.
cd "$(dirname "$0")"
[ -f sublive.pid ] && kill "$(cat sublive.pid)" 2>/dev/null; rm -f sublive.pid
pkill -f '[.]venv/bin/python subctl.py' 2>/dev/null
pkill -f '[m]odels/Qwen3-ASR' 2>/dev/null || true
pkill -f '[m]odels/mt/' 2>/dev/null || true
pkill -f '[l]lama-master-build/bin/llama-server' 2>/dev/null || true   # qwentts server
curl -s -m 60 -X POST 127.0.0.1:8080/v1/vram -H 'Content-Type: application/json' \
     -d '{"reserve_mib": null}' >/dev/null 2>&1
echo stopped
