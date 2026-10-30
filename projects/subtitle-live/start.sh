#!/usr/bin/env bash
# Start the live subtitle overlay (detached; logs to live.log).
# Usage: ./start.sh [--lang it] [--show-de]
cd "$(dirname "$0")"
[ -f sublive.pid ] && kill "$(cat sublive.pid)" 2>/dev/null
sleep 0.5
# ASR server (Qwen3-ASR 0.6B via llama.cpp, port 8095) — only needed in audio
# mode; cue mode reads Prime's own subtitles and never transcribes.
ASR_WANTED=cue
[[ "$*" == *"--mode audio"* ]] && ASR_WANTED=audio
[ -f tuning.json ] && ASR_WANTED=$(.venv/bin/python -c 'import json;t=json.load(open("tuning.json"));print("audio" if t.get("mode")=="audio" or t.get("asr") else "cue")' 2>/dev/null || echo cue)
if [ "$ASR_WANTED" = audio ] && ! curl -sm2 http://127.0.0.1:8095/health >/dev/null; then
  (setsid nohup "$HOME/.unsloth/llama.cpp/build/bin/llama-server" \
     -m models/Qwen3-ASR-0.6B-Q8_0.gguf --mmproj models/mmproj-Qwen3-ASR-0.6B-Q8_0.gguf \
     --host 127.0.0.1 --port 8095 -ngl 99 -c 4096 > asr-server.log 2>&1 < /dev/null &)
  echo "asr-server starting (see asr-server.log)"
  sleep 6
fi
setsid nohup .venv/bin/python sublive.py --asr qwen3asr "$@" >live.log 2>&1 </dev/null &
echo $! > sublive.pid
echo "sublive started (pid $(cat sublive.pid)) — tail -f $(pwd)/live.log"
