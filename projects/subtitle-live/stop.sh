#!/usr/bin/env bash
# Stop the live subtitle overlay (and the Qwen3-ASR server).
cd "$(dirname "$0")"
[ -f sublive.pid ] && kill "$(cat sublive.pid)" 2>/dev/null && echo "stopped" || echo "not running"
rm -f sublive.pid
pkill -f "Qwen3-ASR-0.6B-Q8_0" 2>/dev/null && echo "asr-server stopped"
# TTS server (only runs when tuning.json tts=qwentts); pattern anchored to our build path
pkill -f '[l]lama-master-build/bin/llama-server' 2>/dev/null && echo "tts-server stopped"
# Give the VRAM window back to the Strata engine (sublive does this itself on a
# clean exit; this is the belt-and-braces path):
curl -s -m 60 -X POST 127.0.0.1:8080/v1/vram -H 'Content-Type: application/json' \
     -d '{"reserve_mib": null}' >/dev/null 2>&1
