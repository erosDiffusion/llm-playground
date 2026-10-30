#!/usr/bin/env bash
# Audio-mode ASR: Voxtral Mini 4B Realtime via llama.cpp's streaming audio path.
# Runs on CPU on purpose (-ngl 0 + hidden GPU) so it never fights the dub's GPU
# window: 12 s of German audio in 7.6 s (1.57x realtime, probe 2026-10-30).
# NOTE: transcription follows the model's built-in task format; custom prompts
# (e.g. "translate to English") are NOT honored by llama-mtmd-cli yet.
set -e
cd "$(dirname "$0")"
CLI=../llama-master-build/bin/llama-mtmd-cli
CUDA_VISIBLE_DEVICES="" exec "$CLI" \
  -m models/voxtral/voxtral-realtime-4b-q4km.gguf \
  --mmproj models/voxtral/mmproj-voxtral-realtime-q8.gguf \
  -ngl 0 -t 12 -c 4096 --image "${1:?usage: voxtral_transcribe.sh audio.wav}" \
  -p "Transcribe the audio."
