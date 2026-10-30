# subtitle-live (vault copy)

Provenance: live project at `/home/oem/Apps/deepseek-workspace/subtitle-live`
(machine `oem-am5`, 2026-10-30). Source-only copy — the live dir also holds
`.venv/`, `models/` (kokoro fp16 ONNX + voices, Qwen3 GGUFs, Nemotron NVFP4
~21 GB, piper voices), logs and pidfiles, none of which belong here. Models
are re-downloadable per the README.

# subtitle-live — realtime translated subtitles over a browser tab

When a stream (Prime Video here) only offers German audio/subs, this pipeline
takes the player's own subtitle cues, translates them locally, and feeds the
result back: translated subtitles in the player's own subtitle layer + an
optional realtime dub (TTS). An audio-listening fallback covers any video whose
subtitles are off.

    cue mode:  Prime DOM cues ──► Strata :8080 (DE→EN/IT) ──► in-page sub layer
                                                        └──► piper TTS dub (tab ducked to 0)
    audio mode: PipeWire monitor ──► Qwen3-ASR-0.6B (:8095) ──► LLM ──► window/dub

All local, nothing uploaded. Latency ≈ 1–3 s after speech.
Fallback ASR: `--asr whisper` (faster-whisper, CPU, no GPU needed).

## Use

    ./start.sh                 # English
    ./start.sh --lang it       # Italian
    ./start.sh --show-de       # + small German original above
    tail -f live.log           # watch DE line + translation as they stream
    ./stop.sh                  # stops overlay + ASR server

start.sh auto-starts the ASR server (:8095). It loads ~1.5 GB VRAM — while it
runs, Strata is flexed (`reserve_mib: 5600`). After ./stop.sh, reclaim:
`curl -sX POST 127.0.0.1:8080/v1/vram -H 'Content-Type: application/json' -d '{"reserve_mib": null}'`

## Modes

- **cue (default/auto):** reads Prime's own rendered German subtitles over CDP —
  exact text, complete at cue onset, emitted once per line. No audio needed, no
  ASR. Tab volume auto-ducks to 0 (`--duck 0.3` to keep German under the dub).
  `--feed-subs` writes the translation INTO Prime's subtitle layer (player shows
  EN/IT natively; no floating window — `--keep-overlay` to show both).
- **audio (`--mode audio`):** listens to the speaker signal, Qwen3-ASR → LLM.
  Works for anything playing, incl. subtitles off. Dedup + dub-echo filter on.

    ./start.sh --speak --feed-subs        # the full synced dub setup

Fallbacks: no cues seen 25 s into playback -> auto switches to audio mode;
injection miss (cue element already gone) -> dub speaks the line anyway.

## Live control (subctl + Chrome extension)

`subctl.py` = tiny local control server on **http://127.0.0.1:8321** (loopback
only). It start/stops/restarts the pipeline and edits `tuning.json`, which the
daemon re-reads every 0.5 s — so most knobs apply **live, no restart**.

    .venv/bin/python subctl.py      # control server on http://127.0.0.1:8321

    curl -s localhost:8321/status                       # running? + tuning + log tail
    curl -sX POST localhost:8321/tune -d '{"cue_stable":1,"tts_rate":0.9}'
    curl -sX POST localhost:8321/start      /stop      /restart

Live keys: cue_poll, cue_stable, tts_rate, duck, speak, show_de, feed_subs.
Restart keys: **lang** (voice/prompt language) and **tts** (dub engine).

## Translator model (extension dropdown)

- **Strata** (`:8080`, current agent engine) — best quality + context, ~0.3–0.5 s.
- **Qwen3-1.7B / Qwen3-4B** GGUF (`models/mt/`, served by llama.cpp on `:8096`) —
  ~0.05–0.2 s/line warm (constant prompt prefix is cached). Selecting one in the
  extension **flexes the Strata expert cache to reserve 5 GB** and starts the
  server; picking Strata again stops it and reclaims.
- `madlad400-3b-mt` GGUF is on disk but its 2024 conversion does NOT load in the
  current llama.cpp — kept for a future conversion attempt only.
- **Nemotron 3.5 Transcribe NVFP4** (21.6 GB, `models/nemotron/`): NOT a text
  translator — it is a *SpeechLM* (ASR + direct speech→text translation, 40
  langs, offline). It would replace ASR+LLM in **audio mode** only. Needs vLLM
  0.32 (SpeechLM) + NeMo Speech and ~22 GB VRAM → Strata must be stopped
  (this agent goes offline while it runs). Staged, not yet served.

subctl endpoints: `POST /mt {"model":"qwen3-1.7b"|"qwen3-4b"|"off"}` handles
flex + serve + tuning keys (`mt`, `mt_model`); sublive reads them live.

## Central model roster

`models/roster.json` is the single source of truth for every model the pipeline
knows (translation + speech). `subctl /status` serves it; the extension builds
its Translator dropdown from it live. Add a GGUF under `models/mt/` + a roster
row → it appears in the UI (selectable only when `kind: text-mt,
status: ready`; anything else shows disabled with its status).

Current rows: strata (ready) · qwen3-1.7b / qwen3-4b (ready) · madlad400-3b
(broken: 2024 GGUF won't load in current llama.cpp) · nemotron-transcribe
(staged, audio-mode) · hy-simulmt-30b (watch: **zh↔en only** — Tencent's
simultaneous S2ST, no German/Italian; its GGUF needs llama.cpp support that is
not merged upstream yet, and 30B-A3B won't fit the 15 GB of free disk) ·
gemini-livetranslate (api: cloud only, needs a Google key — no weights) ·
qwen3.8-livetranslate (watch: no public weights).

About the Hy-SimulMT benchmark table (Qwen3.8 / Hy / Gemini3.5 LiveTranslate,
FLEURS 88.4–92.4 etc.): those are **live speech interpreters**, and the whole
evaluation is **zh↔en** (`session.language` accepts only `zh`/`en`). They are
not text translators and have no German path, so they cannot enter the
selectable roster here. In cue mode they are irrelevant — Prime hands us text.
In audio mode the German-capable option we already staged is Nemotron.

## Measured MT bench (2026-10-30, `mtbench.py`)

12 **real** German cues from a live session (register shifts, idioms, cue
artifacts like missing spaces), same prompt shape as `translate()`, greedy,
`enable_thinking:false`. Judged against the German source; n=12 so treat the
counts as indicative. Strata (the agent engine) is the reference.

| backend | EN avg | EN errors/12 | IT avg | IT errors/12 |
|---|---|---|---|---|
| **Strata** (qwen3.8-flash-next) | 0.44 s | 0 (ref) | 0.34 s | 0 (ref) |
| **Qwen3-4B** (in roster) | 0.035 s | 2 | 0.042 s | 3 |
| Qwen3-8B | 0.047 s | 1 | 0.063 s | **5** |
| Gemma 3 4B IT | 0.046 s | 3 | 0.044 s | 4 |

Takeaways: the generalist **8B tier does not pay** — it costs 2x disk and a
9.7 GB flex window and is *worse at Italian* than the 4B we already run
(`le polizie`, `il libreria da sola`). Gemma 3 4B is chatty on fragments and
emits curly quotes. All local models fail the same way on **sentence fragments**
(`…bitten kann, das Gelände zu verlassen`) — that is a context problem, which
is exactly why Strata (with the dialogue context) stays the default and the
small GGUFs are only a speed fallback.

LLaMA 3.1/3.3-8B and Phi-4-mini were **not testable**: HF returns 401 (license
gate). Phi is English-centric anyway; Llama is the weakest of the class for
DE→IT. Google "AI Edge / Gemma on-device" is a mobile deployment path
(LiteRT/MediaPipe), irrelevant to this pipeline.

## Nemotron 3.5 Transcribe (staged, models/nemotron)

SpeechLM: ASR + direct speech→text translation (de→en BLEU ≈40) — **audio
mode only** (titles with no subtitles). In cue mode there is no audio to
transcribe, so it never helps there. Needs vLLM 0.32 + the `nemo_speechlm`
NeMo plugin and ~27 GB VRAM → **stop Strata first; this agent session goes
offline while it runs.**

    ./nemotron_serve.sh --install    # one-time venv (~8 GB)
    # stop Strata, then:
    ./nemotron_serve.sh              # OpenAI-compatible on :8097
    .venv/bin/python nemotron_try.py clip.wav --to English

`nemotron_try.py` posts a base64 wav + the official prompt "Please translate
the given speech to English." — one call replaces ASR+translator.

## Dub voices

Default engine is **Kokoro-82M** (`models/kokoro/`, kokoro-onnx, CPU-only,
RTF ~0.15): `af_bella` (en) / `if_sara` (it) — far more expressive than piper
and 2x faster. Set `"tts": "piper"` in tuning.json to fall back to the old
piper voices. `tts_rate` <1 speaks faster on either engine.

**Qwen3-TTS-12Hz-1.7B** (instruction-controlled emotion, 4.5 GB, Jan 2026) is
the planned premium upgrade — needs a Strata flex window (~6 GB), not installed
yet. Chrome's built-in Translator/TTS checked 2026-10-30: TTS has 0 voices on
this box (dead end); its Translator is worse than the Strata path.
start.sh starts the ASR server **only** in audio mode now (cue never transcribes).

**Chrome extension** (`ext/`): load unpacked via chrome://extensions → Developer
mode → "Load unpacked" → pick `subtitle-live/ext`. The toolbar popup gives
Start/Stop/Restart + sliders/toggles mirroring `tuning.json`, plus a live log
tail. Needs subctl running. `feed_subs` is labelled "(may blackout)" — that's
the DOM-write path; leave it off for the safe floating-window overlay.

## Positioning / look (floating window)

Box is centered bottom by default; tune per window layout:
`--x-frac 0.37 --width-frac 0.6 --bottom-frac 0.24 --tr-pt 24 --de-pt 11`
(bottom-frac 0.24 sits ABOVE Prime's own bottom subtitles; click-through, so
it never blocks the player). `--overlay cdp` = inject into the page instead
(needs CDP attach → shows Chrome's automation banner; not used by default).

## Tuning

- ASR quality: `--model medium` or `--model large-v3` (both already cached on
  this box). large-v3 may lag on CPU; small is realtime on 32 cores.
- `--no-translate` shows the German transcription directly.
- `--url-frag` points at another tab (e.g. netflix.com).
- Capture is system-wide: any sound played through the analog sink is
  transcribed. Mute/pause other players while running.

## Files

- `sublive.py` — the daemon (cue reader, translate, dub, overlay)
- `suboverlay.py` — the click-through GTK overlay window (`/usr/bin/python3`)
- `subctl.py` — control server on `:8321` (start/stop/restart/tune/mt/status+roster)
- `ext/` — MV3 Chrome extension (popup drives subctl; roster-driven dropdown)
- `panel_start.sh` / `panel_stop.sh` — Projects-panel recipes
- `start.sh` / `stop.sh` — plain start/stop (ASR server only in audio mode)
- `mtbench.py` — the translator benchmark used for the table above
- `nemotron_serve.sh` / `nemotron_try.py` — serve + probe the Nemotron SpeechLM
- `cdp_net.py` / `netprobe.py` / `trackprobe.py` — read-only CDP network probes
  (track language lists; never write to the page)
- `peek_player.py` — small CDP probe of the player state
- `probe_tabs.py` — lists Chrome tabs over CDP
- `models/roster.json` — central model table (see above)
- venv: `.venv` (kokoro-onnx, phonemizer, faster-whisper, websockets); CDP client
  reused from `../reels-digest/scripts/cdp.py`
