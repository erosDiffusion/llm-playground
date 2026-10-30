#!/usr/bin/env python3
"""Live translated subtitle overlay for the Prime Video tab.

Pipeline (all local):
  PipeWire monitor of the playing sink  ->  faster-whisper (de ASR)
  -> Strata llama-server :8080 (de -> en/it)  ->  overlay div injected
  into the Prime Video tab via CDP (port 9222).

Usage:  sublive.py [--lang en|it] [--show-de] [--url-frag primevideo.com] [--demo "text"]
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.request

import os as _os
_os.environ.setdefault("ORT_LOGGING_LEVEL", "3")   # mute onnxruntime constant-fold spam

sys.path.insert(0, "/home/oem/Apps/deepseek-workspace/reels-digest/scripts")
from cdp import CDP, Page, CDPError  # noqa: E402

import numpy as np

RATE = 16000
FRAME = int(0.1 * RATE)          # 100 ms frames

# ---------------------------------------------------------------- live tuning
# tuning.json (written by subctl.py / the Chrome extension) overrides CLI args
# at startup, and is re-read every 0.5 s so live knobs apply without restart.
TUNE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tuning.json")
TUNING: dict = {}


def tune(key, default=None):
    return TUNING.get(key, default)


def load_tuning():
    global TUNING
    try:
        with open(TUNE_PATH) as f:
            TUNING = json.load(f)
    except Exception:
        pass


def tune_watch():
    while True:
        time.sleep(0.5)
        load_tuning()
PRE_ROLL = 3                     # 0.3 s of audio kept before speech onset

LANG_NAMES = {"en": "English", "it": "Italian"}

# --------------------------------------------------------------------- audio
def pick_monitor() -> str | None:
    """Return the PipeWire monitor source of a RUNNING sink, else of the default sink."""
    try:
        sources = subprocess.run(["pactl", "list", "short", "sources"],
                                 capture_output=True, text=True, timeout=5).stdout
        states = {}
        full = subprocess.run(["pactl", "list", "sinks"],
                              capture_output=True, text=True, timeout=5).stdout
        for block in full.split("\n\n"):
            m = re.search(r"Name: (\S+)", block)
            s = re.search(r"State: (\S+)", block)
            if m and s:
                states[m.group(1)] = s.group(1)
        default = subprocess.run(["pactl", "get-default-sink"],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
        cands = []
        for line in sources.splitlines():
            name = line.split("\t")[1] if "\t" in line else ""
            if name.endswith(".monitor"):
                sink = name[:-len(".monitor")]
                cands.append((states.get(sink, ""), sink == default, name))
        for running in (True, False):
            for st, is_def, name in cands:
                if (st == "RUNNING") == running:
                    return name
        return cands[0][2] if cands else None
    except Exception:
        return None


class Capturer(threading.Thread):
    """Reads the monitor source, segments speech by energy, pushes PCM chunks."""

    def __init__(self, outq: queue.Queue, source: str | None):
        super().__init__(daemon=True)
        self.outq = outq
        self.source = source
        self.proc = None
        self.stop = False

    def _start_proc(self):
        src = self.source or pick_monitor()
        if not src:
            raise RuntimeError("no monitor source found")
        self.src = src
        self.proc = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
             "-f", "pulse", "-i", src, "-ac", "1", "-ar", str(RATE),
             "-f", "s16le", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        log(f"capturing from {src}")

    def run(self):
        import collections
        while not self.stop:
            try:
                self._start_proc()
            except Exception as e:
                log(f"capture start failed: {e}; retry 3s")
                time.sleep(3)
                continue
            src = self.src
            t_watch = time.time()
            ring = collections.deque(maxlen=PRE_ROLL)
            buf: list[bytes] = []
            voiced = False
            sil_frames = 0
            utter_frames = 0
            floor_win: list[float] = []
            while not self.stop:
                raw = self.proc.stdout.read(FRAME * 2)
                if not raw or len(raw) < FRAME * 2:
                    break
                if self.source is None and time.time() - t_watch > 15:
                    new = pick_monitor()
                    t_watch = time.time()
                    if new and new != src:
                        log(f"audio sink changed -> {new}")
                        self.proc.terminate()
                        break
                x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(x * x)))
                floor_win.append(rms)
                if len(floor_win) > 50:
                    floor_win.pop(0)
                floor = min(floor_win) if len(floor_win) > 20 else 400.0
                gate = max(700.0, floor * 2.8)
                is_v = rms > gate
                ring.append(raw)
                if not voiced:
                    if is_v:
                        voiced = True
                        sil_frames = 0
                        utter_frames = 0
                        buf = list(ring)
                    continue
                utter_frames += 1
                if is_v:
                    sil_frames = 0
                    buf.append(raw)
                else:
                    sil_frames += 1
                    buf.append(raw)
                    if sil_frames >= 6:                    # 0.6 s silence -> end of line
                        self._emit(buf)
                        voiced = False
                        buf = []
                if utter_frames >= 70:                    # hard cut 7 s
                    self._emit(buf)
                    buf = list(ring)
                    utter_frames = 0
                    sil_frames = 0
            if voiced and buf:
                self._emit(buf)
            if not self.stop:
                time.sleep(1.0)

    def _emit(self, buf):
        pcm = b"".join(buf)
        if len(pcm) < int(0.35 * RATE) * 2:               # <0.35 s: ignore
            return
        if self.outq.full():
            try:
                self.outq.get_nowait()                   # drop oldest, stay live
            except queue.Empty:
                pass
        self.outq.put(pcm)


# ------------------------------------------------------------------------ asr
def _wav_b64(pcm: bytes) -> str:
    import base64
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return base64.b64encode(buf.getvalue()).decode()


def asr_qwen(pcm: bytes, args) -> tuple[str, str]:
    """Qwen3-ASR served by llama.cpp llama-server (mtmd audio).
    Returns (text, detected_language)."""
    body = {"model": args.asr_model, "temperature": 0.0, "max_tokens": 300,
            "messages": [{"role": "user", "content": [
                {"type": "input_audio",
                 "input_audio": {"data": _wav_b64(pcm), "format": "wav"}}]}]}
    req = urllib.request.Request(args.asr_url.rstrip("/") + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)["choices"][0]["message"]["content"]
    langm = re.match(r"\s*language (\w+)", out)
    lang = (langm.group(1) if langm else "").lower()
    m = re.search(r"<asr_text>(.*)$", out, re.S)      # Qwen3-ASR output format
    txt = (m.group(1) if m else out).strip()
    return re.sub(r"\s+", " ", txt), lang


def asr_loop(inq: queue.Queue, outq: queue.Queue, args):
    if args.asr == "qwen3asr":
        log(f"ASR: Qwen3-ASR via {args.asr_url}")
        while True:
            pcm = inq.get()
            t0 = time.time()
            try:
                txt, lang = asr_qwen(pcm, args)
            except Exception as e:
                log(f"qwen-asr error: {e}")
                continue
            dt = time.time() - t0
            if len(txt) < 3:
                continue
            log(f"asr {dt:.2f}s ({lang or '?'})")
            outq.put((txt, lang))
        return
    from faster_whisper import WhisperModel
    log(f"loading whisper '{args.model}' (int8, cpu)…")
    model = WhisperModel(args.model, device="cpu", compute_type="int8",
                         cpu_threads=args.asr_threads)
    log("whisper ready")
    vad = args.vad
    while True:
        pcm = inq.get()
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        try:
            segs, _ = model.transcribe(
                audio, language="de", beam_size=1, best_of=1,
                condition_on_previous_text=False,
                vad_filter=vad,
                vad_parameters=dict(min_speech_duration=0.3),
                log_progress=False)
            parts, probs = [], []
            for s in segs:
                parts.append(s.text.strip())
                probs.append((s.avg_logprob, s.no_speech_prob))
        except Exception as e:
            log(f"asr error: {e}; disabling vad filter")
            vad = False
            continue
        txt = " ".join(parts).strip()
        if len(txt) < 3:
            continue
        if probs and all(p[1] > 0.8 for p in probs):
            continue
        if probs and sum(p[0] for p in probs) / len(probs) < -1.35:
            continue
        outq.put((txt, "german"))


# ------------------------------------------------------------------ translate
def translate(de: str, ctx: list[str], args) -> str:
    lang = LANG_NAMES[args.lang]
    src = str(tune("src_lang", "German")).rstrip(".")
    sysmsg = (f"You localize live subtitles for a TV series/movie. Input is one "
              f"{src} subtitle line (it may contain transcription errors; "
              f"use context to correct obvious mistakes). Translate it into natural, "
              f"concise {lang} for on-screen subtitles. Output ONLY the translated line, "
              f"plain text, no quotes, no notes.")
    user = ""
    if ctx:
        user += "Previous translated lines (context only):\n" + "\n".join(ctx[-3:]) + "\n\n"
    user += f"German line:\n{de}"
    mt = str(tune("mt", "strata"))
    url, model = args.llm_url, args.llm_model
    if mt == "local":
        url = "http://127.0.0.1:8096"
        model = str(tune("mt_model", "qwen3-1.7b"))
    body = {
        "model": model, "max_tokens": 220, "temperature": 0.25,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "system", "content": sysmsg},
                     {"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        msg = json.load(r)["choices"][0]["message"]
    out = (msg.get("content") or "").strip()
    out = re.sub(r"^['\"“”]\s*|\s*['\"“”]$", "", out)
    return out.split("\n")[0][:240]


# -------------------------------------------------------------------- overlay
INJECT_JS = r"""
(() => {
  if (window.__dshSub) return true;
  const w = document.createElement('div');
  w.id = '__dshsub';
  w.setAttribute('style',
    'position:fixed;left:50%;transform:translateX(-50%);bottom:9%;z-index:2147480000;' +
    'max-width:82%;text-align:center;font-family:system-ui,Segoe UI,Roboto,sans-serif;' +
    'pointer-events:none;transition:opacity .4s;opacity:0;');
  const de = document.createElement('div');
  de.setAttribute('style', 'font-size:clamp(14px,1.5vw,22px);color:#cfcfcf;' +
    'text-shadow:0 1px 3px #000;margin-bottom:.35em;');
  const tr = document.createElement('div');
  tr.setAttribute('style', 'font-size:clamp(24px,3.4vw,54px);font-weight:700;color:#fff;' +
    'line-height:1.25;background:rgba(0,0,0,.4);padding:.15em .55em;border-radius:.35em;' +
    'display:inline-block;text-shadow:0 0 6px #000,0 2px 4px rgba(0,0,0,.9);');
  w.appendChild(de); w.appendChild(tr);
  (document.fullscreenElement || document.documentElement).appendChild(w);
  window.__dshSub = function (trText, deText) {
    const host = document.fullscreenElement || document.documentElement;
    if (w.parentElement !== host) host.appendChild(w);
    de.textContent = deText || '';
    de.style.display = deText ? 'block' : 'none';
    tr.textContent = trText || '';
    w.style.opacity = (trText || deText) ? '1' : '0';
    clearTimeout(window.__dshSubT);
    const hold = Math.max(3200, (trText || '').length * 120 + 800);
    window.__dshSubT = setTimeout(() => { w.style.opacity = '0'; }, hold);
    return true;
  };
  window.__dshSubKill = function () {
    const e = document.getElementById('__dshsub');
    if (e) e.remove();
    window.__dshSub = null;
    return true;
  };
  return true;
})()
"""


class Overlay:
    def __init__(self, args):
        self.args = args
        self.cdp: CDP | None = None
        self.page: Page | None = None

    def _attach(self):
        if self.cdp:
            try:
                self.cdp.close()
            except Exception:
                pass
        self.cdp = CDP.connect(port=self.args.cdp_port, attempts=6)
        targets = self.cdp.send("Target.getTargets")["targetInfos"]
        tid = next((t["targetId"] for t in targets
                    if t.get("type") == "page" and self.args.url_frag in t.get("url", "")),
                   None)
        if not tid:
            raise CDPError(f"no tab matching {self.args.url_frag!r}")
        sid = self.cdp.send("Target.attachToTarget",
                            {"targetId": tid, "flatten": True})["sessionId"]
        self.page = Page(tid, sid)
        self.cdp.evaluate(self.page, INJECT_JS, timeout=10)
        log(f"overlay attached to tab {tid[:8]}")

    def show(self, tr: str, de: str):
        expr = (f"window.__dshSub && window.__dshSub({json.dumps(tr)},"
                f" {json.dumps(de) if self.args.show_de else ''})")
        for attempt in range(2):
            try:
                if not self.page:
                    self._attach()
                v = self.cdp.evaluate(self.page, expr, timeout=8)
                if v:
                    return True
            except Exception as e:
                log(f"overlay re-attach ({e})")
                self.page = None
                try:
                    self._attach()
                except Exception as e2:
                    log(f"attach failed: {e2}")
                    time.sleep(3)
        return False

    def kill(self):
        try:
            if self.page:
                self.cdp.evaluate(self.page, "window.__dshSubKill && __dshSubKill()", timeout=5)
        except Exception:
            pass


class WindowOverlay:
    """Desktop always-on-top click-through window (no Chrome attach, no banner)."""

    def __init__(self, args):
        import os
        self.args = args
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "suboverlay.py")
        self.p = subprocess.Popen(
            ["/usr/bin/python3", path,
             "--x-frac", str(args.x_frac), "--width-frac", str(args.width_frac),
             "--bottom-frac", str(args.bottom_frac),
             "--tr-pt", str(args.tr_pt), "--de-pt", str(args.de_pt)],
            stdin=subprocess.PIPE, text=True, bufsize=1)

    def show(self, tr: str, de: str, rect: dict | None = None) -> bool:
        hold = max(3200, len(tr) * 120 + 800)
        try:
            self.p.stdin.write(json.dumps(
                {"tr": tr, "de": de if tune("show_de", self.args.show_de) else "",
                 "hold_ms": hold, "rect": rect}) + "\n")
            self.p.stdin.flush()
            return True
        except Exception as e:
            log(f"window overlay dead: {e}")
            return False

    def place(self, rect: dict | None):
        """Reposition (no text change) so the box tracks the browser window."""
        if not rect:
            return
        try:
            self.p.stdin.write(json.dumps({"place": rect}) + "\n")
            self.p.stdin.flush()
        except Exception:
            pass

    def style(self, tr_pt, de_pt, bottom_frac, width_frac):
        """Live restyle (font sizes independently + vertical position)."""
        try:
            self.p.stdin.write(json.dumps(
                {"style": {"tr_pt": tr_pt, "de_pt": de_pt,
                           "bottom_frac": bottom_frac, "width_frac": width_frac}
                 }) + "\n")
            self.p.stdin.flush()
            return True
        except Exception:
            return False

    def kill(self):
        try:
            self.p.terminate()
        except Exception:
            pass


class Dub:
    """Speak the translated line through the speakers (CPU TTS).
    Engine: kokoro (default — far more expressive, ~2x faster) with
    piper as automatic fallback."""

    VOICES = {"en": "en_US-lessac-medium", "it": "it_IT-paola-medium"}
    KOKORO = {  # phonemizer lang, {gender: voice}
        "en": ("en-us", {"female": "af_bella", "male": "am_michael"}),
        "it": ("it", {"female": "if_sara", "male": "im_nicola"}),
    }

    def __init__(self, args):
        import os
        self.args = args
        self.engine = "piper"
        self.kokoro = None
        here = os.path.dirname(os.path.abspath(__file__))
        want = str(tune("tts", getattr(args, "tts", "auto")))
        if want in ("auto", "kokoro"):
            try:
                import onnxruntime as rt
                from kokoro_onnx import Kokoro
                model = os.path.join(here, "models", "kokoro", "kokoro-v1.0.fp16.onnx")
                so = rt.SessionOptions()
                so.log_severity_level = 3          # mute constant-fold CPU warnings
                sess = rt.InferenceSession(model, sess_options=so,
                                           providers=["CPUExecutionProvider"])
                sess._model_path = model
                self.kokoro = Kokoro.from_session(
                    sess, os.path.join(here, "models", "kokoro", "voices-v1.0.bin"))
                self.engine = "kokoro"
                log(f"dub voice: kokoro "
                    f"{self.KOKORO[args.lang][1].get(tune('voice', 'female'), 'af_bella')}")
            except Exception as e:
                log(f"kokoro unavailable ({e}) — falling back to piper")
        if self.engine == "piper":
            from piper import PiperVoice
            name = self.VOICES[args.lang]
            path = os.path.join(here, "models", "voices", name + ".onnx")
            self.voice = PiperVoice.load(path)
            self.cfg = None
            self._rate = args.tts_rate
            try:
                from piper.config import SynthesisConfig
                self.cfg = SynthesisConfig(length_scale=args.tts_rate)
            except Exception:
                pass
            log(f"dub voice: piper {self.VOICES[args.lang]}")
        self.q = queue.Queue()
        self.proc = None
        threading.Thread(target=self._worker, daemon=True).start()

    def speak(self, text: str):
        if text:
            self.q.put(text)

    def _worker(self):
        while True:
            text = self.q.get()
            # drain: only speak the most recent line, drop stale ones
            try:
                while True:
                    text = self.q.get_nowait()
            except queue.Empty:
                pass
            if self.proc:
                try:
                    self.proc.kill()      # new line interrupts the previous voice
                except Exception:
                    pass
            self._play(text)

    def _play(self, text: str):
        try:
            rate = float(tune("tts_rate", self.args.tts_rate))
            if self.engine == "kokoro":
                self._play_kokoro(text, rate)
                return
            cfg = self.cfg
            if self.cfg is not None and rate != getattr(self, "_rate", None):
                try:
                    from piper.config import SynthesisConfig
                    cfg = self.cfg = SynthesisConfig(length_scale=rate)
                    self._rate = rate
                except Exception:
                    pass
            chunks = (self.voice.synthesize(text, cfg) if cfg
                      else self.voice.synthesize(text))
            aplay, sr = None, None
            for ch in chunks:
                arr = getattr(ch, "audio_float_array", None)
                if arr is None or len(arr) == 0:
                    continue
                raw = (np.clip(arr, -1, 1) * 32767).astype(np.int16).tobytes()
                if aplay is None:
                    sr = getattr(ch, "sample_rate", 22050)
                    aplay = subprocess.Popen(["aplay", "-q", "-f", "S16_LE", "-t", "raw",
                                              "-r", str(sr)],
                                             stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    self.proc = aplay
                aplay.stdin.write(raw)
            if aplay:
                aplay.stdin.close()
                aplay.wait()
            if self.proc is aplay:
                self.proc = None
        except Exception as e:
            log(f"dub error: {e}")

    def _play_kokoro(self, text: str, rate: float):
        # kokoro `speed` is the inverse of piper's length_scale; stream chunks
        # so aplay starts on the first batch (parity with piper's low latency)
        import asyncio
        lang, voices = self.KOKORO[self.args.lang]
        voice = voices.get(str(tune("voice", "female")), voices["female"])
        speed = max(0.5, min(2.0, 1.0 / rate))

        async def run():
            aplay = None
            try:
                gen = self.kokoro.create_stream(text, voice=voice, speed=speed, lang=lang)
                async for audio, sr in gen:
                    raw = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
                    if aplay is None:
                        aplay = subprocess.Popen(
                            ["aplay", "-q", "-f", "S16_LE", "-t", "raw", "-r", str(sr)],
                            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        self.proc = aplay
                    aplay.stdin.write(raw)
                if aplay:
                    aplay.stdin.close()
                    aplay.wait()
            finally:
                if self.proc is aplay:
                    self.proc = None

        asyncio.run(run())


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9äöüß ]+", "", s.lower()).strip()


class CueReader:
    """Reads Prime's own subtitle cues + player state via CDP (cue/synced mode).
    Text is complete at cue onset -> emit once, perfectly bounded."""

    CUE_SELS = ['[class*="static-layer"]', '[class*="pac-subtitle"]',
                '[class*="subtitleLayer"]', '[class*="subtitle"]',
                '[class*="caption"]']

    def __init__(self, args):
        self.args = args
        self.cdp = None
        self.page = None
        self.current_tr = ""
        self.current_de = ""
        self.last_rect = None

    def set_sub(self, stamp: str, de: str = "") -> bool:
        """Publish a bilingual stamp (original + \\n + translation).
        The page-side observer re-applies it whenever Prime re-renders the cue
        back to this exact original line — and never onto a different cue."""
        return bool(self._eval(f"""(() => {{
            window.__dshTr = {json.dumps(stamp)};
            window.__dshOrig = {json.dumps(de)};
            const e = document.querySelector('[data-dsh]');
            if (e && e.textContent.trim() !== window.__dshTr) {{
                e.style.whiteSpace = 'pre-line';
                e.textContent = window.__dshTr;
            }}
            return !!e;
        }})()"""))

    def clear_tr(self):
        """Stop stamping (a new cue started; show its original until translated)."""
        self._eval("window.__dshTr = ''; window.__dshOrig = '';")

    _INJECT = """(() => {
        if (window.__dshMO) { try { window.__dshMO.disconnect(); } catch (e) {} }
        window.__dshTr = ''; window.__dshOrig = '';
        const stamp = () => {
            const want = window.__dshTr, orig = window.__dshOrig;
            if (!want) return;
            const e = document.querySelector('[data-dsh]');
            if (!e) return;
            const t = (e.textContent || '').trim();
            if (t === want) return;                 // already showing ours
            if (t === orig) {                       // Prime re-rendered THIS cue
                e.style.whiteSpace = 'pre-line';
                e.textContent = want;
            }
        };
        window.__dshMO = new MutationObserver(stamp);
        window.__dshMO.observe(document.body,
            {subtree: true, childList: true, characterData: true});
        return 'installed';
    })()"""

    def _attach(self):
        if self.cdp:
            try:
                self.cdp.close()
            except Exception:
                pass
        self.cdp = CDP.connect(port=self.args.cdp_port, attempts=6)
        targets = self.cdp.send("Target.getTargets")["targetInfos"]
        tid = next((t["targetId"] for t in targets
                    if t.get("type") == "page" and self.args.url_frag in t.get("url", "")),
                   None)
        if not tid:
            raise CDPError(f"no tab matching {self.args.url_frag!r}")
        sid = self.cdp.send("Target.attachToTarget",
                            {"targetId": tid, "flatten": True})["sessionId"]
        self.page = Page(tid, sid)
        log(f"cue reader attached to tab {tid[:8]}")
        if self.args.feed_subs:
            try:
                log(f"page observer: {self._eval(self._INJECT)}")
            except Exception as e:
                log(f"observer install failed: {e}")

    def _eval(self, expr):
        if not self.page:
            self._attach()
        return self.cdp.evaluate(self.page, expr, timeout=8)

    def state(self) -> dict:
        sels = json.dumps(self.CUE_SELS)
        expr = f"""(() => {{
          const v = document.querySelector('video');
          let txt = '';
          let best = null, bestA = Infinity;
          for (const s of {sels}) {{
            for (const el of document.querySelectorAll(s)) {{
              if (el.closest('button,[role="menu"],[role="dialog"],nav')) continue;
              if (el.querySelector('video')) continue;      // never a player container
              const t = (el.textContent || '').trim();
              if (t.length < 2 || t.length > 700) continue;
              const r = el.getBoundingClientRect();
              if (r.height < 8 || r.width < 8) continue;    // must be actually rendered
              const own = [...el.childNodes].some(n => n.nodeType === 3
                              && (n.textContent || '').trim());
              const a = r.width * r.height * (own ? 1 : 1e6);  // prefer real text leaves
              if (a < bestA) {{ bestA = a; best = el; }}
            }}
          }}
          if (best) {{
            best.setAttribute('data-dsh', '1');
            txt = (best.textContent || '').trim();
          }}
          return JSON.stringify({{t: v ? v.currentTime : 0, paused: v ? v.paused : true,
                                  vol: v ? v.volume : 1, sub: txt.slice(0, 700),
                                  win: {{sx: window.screenX, sy: window.screenY,
                                        oh: window.outerHeight, ih: window.innerHeight}},
                                  wr: (() => {{
                                    if (!v) return null;
                                    const r = v.getBoundingClientRect();
                                    return {{x: r.x, y: r.y, w: r.width, h: r.height}};
                                  }})()}});
        }})()"""
        return json.loads(self._eval(expr))

    def set_volume(self, vol: float):
        self._eval(f"document.querySelector('video').volume = {vol}")

    @staticmethod
    def screen_rect(st: dict) -> dict | None:
        """Screen-space rect of the <video> element (CSS px ≈ X11 px @100%).
        Combines window.screenX/Y, the browser chrome height (outer-inner),
        and the video's bounding box within the viewport."""
        win, wr = st.get("win"), st.get("wr")
        if not win or not wr or wr["w"] < 50:
            return None
        chrome = max(0, win["oh"] - win["ih"])
        return {"x": win["sx"] + wr["x"], "y": win["sy"] + chrome + wr["y"],
                "w": wr["w"], "h": wr["h"]}


# ---------------------------------------------------------------------- main
_T0 = time.time()


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def cue_feed(cue: "CueReader", tq: queue.Queue, args, on_no_cues=None, on_rect=None):
    last, pending, stable, t_vol = "", "", 0, 0.0
    saw_cue, playing_t0, t_rect = False, None, 0.0
    while True:
        try:
            st = cue.state()
        except Exception as e:
            log(f"cue read failed: {e} — re-attaching")
            cue.page = None
            time.sleep(1)
            continue
        cue.last_rect = CueReader.screen_rect(st)
        if on_rect and cue.last_rect and time.time() - t_rect > 1.0:
            on_rect(cue.last_rect)
            t_rect = time.time()
        fs = bool(tune("feed_subs", args.feed_subs))
        d = float(tune("duck", args.duck))
        if (not st["paused"] and d < 1 and time.time() - t_vol > 3
                and abs(st["vol"] - d) > 0.01):
            try:
                cue.set_volume(d)
                t_vol = time.time()
            except Exception:
                pass
        if not st["paused"]:
            if playing_t0 is None:
                playing_t0 = time.time()
            if st["sub"]:
                saw_cue = True
            elif (on_no_cues and not saw_cue
                  and time.time() - playing_t0 > 25):
                log("cue mode: 25 s played with no subtitle cues — subtitles probably OFF. "
                    "Falling back to AUDIO mode (enable German subs and restart for exact sync).")
                on_no_cues()
                return
        n = norm(st["sub"])
        trn = norm(cue.current_tr)
        if fs and trn and n and n == norm(last):
            # Prime re-rendered the original cue text -> re-apply our translation
            try:
                cue.set_sub(cue.current_tr, cue.current_de)
            except Exception:
                pass
        if n and n != norm(last) and n != trn:
            if n == norm(pending):
                stable += 1
                if stable >= int(tune("cue_stable", args.cue_stable)):
                    last = st["sub"]
                    tq.put((st["sub"], "cue"))
                    stable = 0
            else:
                if fs:
                    try:
                        cue.clear_tr()   # new cue: show its text until we translate it
                    except Exception:
                        pass
                pending = st["sub"]
                stable = 0
        time.sleep(float(tune("cue_poll", args.cue_poll)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["en", "it"], default="en")
    ap.add_argument("--asr", choices=["whisper", "qwen3asr"], default="whisper")
    ap.add_argument("--asr-url", default="http://127.0.0.1:8095")
    ap.add_argument("--asr-model", default="qwen3-asr-0.6b")
    ap.add_argument("--show-de", action="store_true", help="also show the German original (small)")
    ap.add_argument("--model", default="small")
    ap.add_argument("--asr-threads", type=int, default=16)
    ap.add_argument("--overlay", choices=["window", "cdp"], default="window",
                    help="window = desktop always-on-top (no Chrome banner); "
                         "cdp = inject into the tab")
    ap.add_argument("--x-frac", type=float, default=0.5,
                    help="subtitle box center, fraction of screen width")
    ap.add_argument("--width-frac", type=float, default=0.66)
    ap.add_argument("--bottom-frac", type=float, default=0.10)
    ap.add_argument("--tr-pt", type=int, default=30)
    ap.add_argument("--de-pt", type=int, default=13)
    ap.add_argument("--url-frag", default="primevideo.com")
    ap.add_argument("--cdp-port", type=int, default=9222)
    ap.add_argument("--source", default=None, help="pulse source override")
    ap.add_argument("--vad", action="store_true", help="extra silero VAD inside whisper")
    ap.add_argument("--llm-url", default="http://127.0.0.1:8080")
    ap.add_argument("--llm-model", default="qwen3.8-flash-next-iq3_s")
    ap.add_argument("--no-translate", action="store_true", help="show raw German only")
    ap.add_argument("--speak", action="store_true", help="dub: speak the translation via TTS")
    ap.add_argument("--tts-rate", type=float, default=1.0, help="<1 faster, >1 slower")
    ap.add_argument("--tts", default="auto", choices=["auto", "kokoro", "piper"],
                    help="dub engine (kokoro = expressive default, piper fallback)")
    ap.add_argument("--mode", choices=["auto", "cue", "audio"], default="auto",
                    help="cue = read Prime's own subtitles (exact text+timing, one emit "
                         "per line, tab auto-ducked); audio = listen via ASR; "
                         "auto = cue if cues are visible, else audio")
    ap.add_argument("--duck", type=float, default=1.0,
                    help="set tab volume to this in cue mode (default 1.0 = never "
                         "touch the player's sound; you control volume)")
    ap.add_argument("--cue-poll", type=float, default=0.15,
                    help="cue mode: seconds between subtitle reads (lower = snappier)")
    ap.add_argument("--cue-stable", type=int, default=2,
                    help="cue mode: consecutive identical reads required before "
                         "translating (lower = faster, slight risk of half-lines)")
    ap.add_argument("--feed-subs", action="store_true",
                    help="cue mode: write the translation INTO Prime's subtitle layer "
                         "(the player itself shows English/Italian; no floating window)")
    ap.add_argument("--keep-overlay", action="store_true",
                    help="with --feed-subs, also keep the floating window")
    ap.add_argument("--demo", default=None, help="inject one demo line, no audio pipeline")
    args = ap.parse_args()

    load_tuning()
    if TUNING:
        for k in ("lang", "asr", "mode", "duck", "cue_poll", "cue_stable", "tts_rate",
                  "tts", "speak", "show_de", "feed_subs", "x_frac", "width_frac",
                  "bottom_frac", "tr_pt", "de_pt"):
            if k in TUNING:
                setattr(args, k, TUNING[k])
        threading.Thread(target=tune_watch, daemon=True).start()

    # Always create the window + dub workers so feed_subs / speak can be
    # toggled live from the extension (the feed path just doesn't call ov.show).
    ov = WindowOverlay(args) if args.overlay == "window" else Overlay(args)
    dub = Dub(args)   # always loaded so --speak / dub toggle works live
    cue = None

    def style_watch():
        """Push font-size / vertical-position changes to the overlay live."""
        if not isinstance(ov, WindowOverlay):
            return
        last = None
        while True:
            time.sleep(0.4)
            cur = (int(tune("tr_pt", args.tr_pt)), int(tune("de_pt", args.de_pt)),
                   float(tune("bottom_frac", args.bottom_frac)),
                   float(tune("width_frac", args.width_frac)))
            if cur != last:
                ov.style(*cur)
                last = cur
    threading.Thread(target=style_watch, daemon=True).start()

    def bye(*_):
        log("stopping; removing overlay")
        if cue and float(tune("duck", args.duck)) < 1:
            try:
                cue.set_volume(1.0)     # give the tab its audio back (only if we ducked)
            except Exception:
                pass
        if ov:
            ov.kill()
        sys.exit(0)
    signal.signal(signal.SIGTERM, bye)
    signal.signal(signal.SIGINT, bye)

    if args.demo:
        ok = ov.show(args.demo if not args.no_translate else "Demo", "Demo – deutsche Zeile") if ov else False
        log(f"demo injected: {ok}; sleeping 6s")
        time.sleep(6)
        ov.kill()
        return

    tq = queue.Queue(maxsize=8)
    audio_started = {"v": False}

    def start_audio():
        if audio_started["v"]:
            return
        audio_started["v"] = True
        aq = queue.Queue(maxsize=3)
        Capturer(aq, args.source).start()
        threading.Thread(target=asr_loop, args=(aq, tq, args), daemon=True).start()
        log("mode: AUDIO — ASR listens to tab audio (dedup + echo filter on)")

    source = "audio"
    if args.mode in ("auto", "cue"):
        cue = CueReader(args)
        try:
            cue.state()                       # probe attach to the player tab
            source = "cue"
            log("mode: CUE — reading Prime's own subtitle cues. One line, once, "
                "as soon as it is complete" +
                (f"; tab volume -> {args.duck:.2f}" if args.duck < 1
                 else "; player sound untouched (you control volume)"))
            _onrect = ov.place if isinstance(ov, WindowOverlay) else None
            threading.Thread(target=cue_feed,
                             args=(cue, tq, args, start_audio, _onrect),
                             daemon=True).start()
        except Exception as e:
            log(f"cue mode unavailable ({e}) — using AUDIO mode")
            cue = None
    if source == "audio":
        start_audio()

    def sim(a: str, b: str) -> float:
        wa, wb = set(a.split()), set(b.split())
        return len(wa & wb) / max(1, min(len(wa), len(wb)))

    ctx: list[str] = []
    recent_src: list[str] = []
    recent_out: list[str] = []
    while True:
        de, lang = tq.get()
        n = norm(de)
        if not n or any(n == r or (len(n) > 12 and (n in r or r in n)) for r in recent_src):
            log(f"dup skipped: {de[:60]!r}")
            continue
        recent_src.append(n)
        recent_src = recent_src[-6:]
        if dub and lang == LANG_NAMES[args.lang].lower():
            log("echo skipped (heard our own dub voice)")
            continue
        t0 = time.time()
        try:
            tr = de if args.no_translate else translate(de, ctx, args)
        except Exception as e:
            log(f"translate failed ({e}) — showing original")
            tr = de
        ntr = norm(tr)
        if any(sim(ntr, r) >= 0.8 for r in recent_out):
            log(f"repeated translation skipped: {tr[:60]!r}")
            continue
        ctx.append(tr)
        ctx = ctx[-3:]
        recent_out.append(ntr)
        recent_out = recent_out[-2:]
        dt = time.time() - t0
        log(f"DE: {de}")
        log(f"{args.lang.upper()}: {tr}   (llm {dt:.1f}s)")
        if tune("feed_subs", args.feed_subs) and cue:
            stamp = f"{de}\n{tr}"          # bilingual: original + newline + translation
            try:
                cue.current_tr = stamp
                cue.current_de = de
                if not cue.set_sub(stamp, de):
                    log("sub injection: cue element already gone — dub only for this line")
                    if ov:
                        ov.show(tr, de)
            except Exception as e:
                log(f"sub injection failed: {e}")
                if ov:
                    ov.show(tr, de)     # fall back to the window if injection failed
        elif ov:
            ov.show(tr, de)
        if dub and tune("speak", args.speak):
            dub.speak(tr)


if __name__ == "__main__":
    main()
