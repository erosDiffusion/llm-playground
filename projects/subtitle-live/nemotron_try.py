#!/usr/bin/env python3
"""Try Nemotron Transcribe on a wav: transcribe OR translate speech.

Server must be up: ./nemotron_serve.sh  (Strata stopped!)
Usage:
  nemotron_try.py audio.wav                 -> transcript
  nemotron_try.py audio.wav --to English    -> speech translation to English
"""
import argparse
import base64
import json
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("wav")
ap.add_argument("--to", default=None, help="target language, e.g. English")
ap.add_argument("--url", default="http://127.0.0.1:8097/v1")
args = ap.parse_args()

prompt = (f"Please translate the given speech to {args.to}." if args.to
          else "Transcribe with punctuation and capitalization.")
audio = base64.b64encode(open(args.wav, "rb").read()).decode()

body = {
    "model": "nemotron-transcribe",
    "temperature": 0,
    "chat_template_kwargs": {"enable_thinking": False},
    "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "audio_url", "audio_url": {"url": f"data:audio/wav;base64,{audio}"}},
    ]}],
}
req = urllib.request.Request(args.url.rstrip("/") + "/chat/completions",
                             data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=300) as r:
    print(json.load(r)["choices"][0]["message"]["content"])
