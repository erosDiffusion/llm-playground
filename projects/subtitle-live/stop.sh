#!/usr/bin/env bash
# Stop the live subtitle overlay (and the Qwen3-ASR server).
cd "$(dirname "$0")"
[ -f sublive.pid ] && kill "$(cat sublive.pid)" 2>/dev/null && echo "stopped" || echo "not running"
rm -f sublive.pid
pkill -f "Qwen3-ASR-0.6B-Q8_0" 2>/dev/null && echo "asr-server stopped"
# Optional: give the VRAM window back to the Strata engine:
#   curl -sX POST 127.0.0.1:8080/v1/vram -H 'Content-Type: application/json' -d '{"reserve_mib": null}'
