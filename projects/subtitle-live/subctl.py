#!/usr/bin/env python3
"""subctl — tiny local control server for subtitle-live (used by the Chrome
extension and curl). Binds 127.0.0.1 only.

Endpoints (CORS enabled for the extension):
  GET  /status   -> {running, pid, tuning, log}          (log = last 2000 chars)
  POST /tune     -> body: json of tuning keys; merges into tuning.json
  POST /start    -> runs start.sh (sublive re-reads tuning.json at startup)
  POST /stop     -> runs stop.sh
  POST /restart  -> stop + start
Keys needing restart: lang (loads a different voice/prompt language).
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
TUNE = os.path.join(HERE, "tuning.json")
PIDF = os.path.join(HERE, "sublive.pid")
LOG = os.path.join(HERE, "live.log")
PORT = 8321
NEEDS_RESTART = {"lang", "tts"}

_lock = threading.Lock()

ROSTER = os.path.join(HERE, "models", "roster.json")


def read_roster() -> list:
    try:
        return json.load(open(ROSTER)).get("models", [])
    except Exception:
        return []


def mt_models() -> dict:
    """id -> gguf path; only roster entries that llama.cpp can serve today."""
    return {m["id"]: m["path"] for m in read_roster()
            if m.get("kind") == "text-mt" and m.get("status") == "ready"
            and m.get("path")}


MT_PID = os.path.join(HERE, "mt.pid")
LLAMA = os.path.expanduser("~/.unsloth/llama.cpp/build/bin/llama-server")


def mt_running():
    try:
        pid = int(open(MT_PID).read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def flex(mib):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8080/v1/vram",
            data=json.dumps({"reserve_mib": mib}).encode(),
            headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=60))
    except Exception as e:
        return {"error": str(e)}


def mt_stop(reclaim=True):
    pid = mt_running()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        try:
            os.remove(MT_PID)
        except Exception:
            pass
    if reclaim:
        flex(None)


def mt_start(model):
    gg = mt_models().get(model)
    if not gg or not os.path.exists(os.path.join(HERE, gg)):
        return f"model '{model}' not in roster (or not downloaded)"
    mt_stop(reclaim=False)
    f = flex(5120)
    lf = open(os.path.join(HERE, "mt-server.log"), "wb")
    p = subprocess.Popen([LLAMA, "-m", os.path.join(HERE, gg), "--host", "127.0.0.1",
                          "--port", "8096", "-ngl", "99", "-c", "4096"],
                         stdout=lf, stderr=lf, start_new_session=True)
    open(MT_PID, "w").write(str(p.pid))
    for _ in range(30):
        time.sleep(1)
        try:
            if urllib.request.urlopen("http://127.0.0.1:8096/health",
                                      timeout=2).status == 200:
                return {"ok": True, "pid": p.pid, "flex": f}
        except Exception:
            pass
    return {"ok": False, "error": "mt server did not come up (see mt-server.log)"}


def read_tuning() -> dict:
    try:
        return json.load(open(TUNE))
    except Exception:
        return {}


def running_pid():
    try:
        pid = int(open(PIDF).read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def do(script: str) -> str:
    r = subprocess.run(["bash", os.path.join(HERE, script)],
                       cwd=HERE, capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr).strip()


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/status"):
            tail = ""
            try:
                with open(LOG, "rb") as f:
                    f.seek(max(0, os.path.getsize(LOG) - 2000))
                    tail = f.read().decode("utf-8", "replace")
            except Exception:
                pass
            pid = running_pid()
            self._send({"running": pid is not None, "pid": pid,
                        "mt": mt_running() is not None,
                        "roster": [m for m in read_roster()
                                   if m.get("kind") in ("text-mt", "speech")],
                        "tuning": read_tuning(), "log": tail})
        else:
            self._send({"error": "unknown"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        if self.path.startswith("/tune"):
            try:
                patch = json.loads(raw)
                assert isinstance(patch, dict)
            except Exception:
                self._send({"error": "bad json"}, 400)
                return
            with _lock:
                t = read_tuning()
                before = dict(t)
                t.update(patch)
                json.dump(t, open(TUNE, "w"), indent=1)
            changed_restart = sorted(k for k in NEEDS_RESTART
                                     if t.get(k) != before.get(k))
            self._send({"ok": True, "tuning": t,
                        "needRestart": changed_restart})
        elif self.path.startswith("/start"):
            self._send({"ok": True, "out": do("start.sh")})
        elif self.path.startswith("/stop"):
            self._send({"ok": True, "out": do("stop.sh")})
        elif self.path.startswith("/restart"):
            do("stop.sh")
            self._send({"ok": True, "out": do("start.sh")})
        elif self.path.startswith("/mt"):
            try:
                body = json.loads(raw or b"{}")
                model = body.get("model", "")
                assert isinstance(model, str)
            except Exception:
                self._send({"error": "bad json"}, 400)
                return
            with _lock:
                t = read_tuning()
                if model == "off":
                    t.update({"mt": "strata"})
                    json.dump(t, open(TUNE, "w"), indent=1)
                    mt_stop()
                    self._send({"ok": True, "out": "local mt server stopped; strata full"})
                else:
                    r = mt_start(model)
                    if isinstance(r, dict) and r.get("ok"):
                        t.update({"mt": "local", "mt_model": model})
                        json.dump(t, open(TUNE, "w"), indent=1)
                    self._send(r if isinstance(r, dict) else {"ok": False, "error": r})
        else:
            self._send({"error": "unknown"}, 404)


if __name__ == "__main__":
    print(f"subctl on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
