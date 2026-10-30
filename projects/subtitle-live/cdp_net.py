"""Network-level CDP client: event queue + safe RPC (no Runtime calls needed)."""
from __future__ import annotations

import json
import os
import queue
import threading
import time

import websockets.sync.client as ws


def find_endpoint(port: int = 9222) -> str:
    pap = os.path.expanduser("~/.config/google-chrome/DevToolsActivePort")
    lines = open(pap).read().split()
    if len(lines) < 2:
        raise RuntimeError("DevToolsActivePort missing")
    return f"ws://127.0.0.1:{lines[0]}{lines[1]}"


class CDPNet:
    def __init__(self, port: int = 9222):
        self.ws = ws.connect(find_endpoint(port), max_size=128 * 1024 * 1024,
                             ping_interval=20, open_timeout=10)
        self._lock = threading.Lock()
        self._nid = 0
        self._pending: dict[int, list] = {}
        self.events: queue.Queue = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        try:
            for raw in self.ws:
                msg = json.loads(raw)
                if "id" in msg:
                    box = self._pending.get(msg["id"])
                    if box is not None:
                        box.append(msg)
                else:
                    self.events.put((msg.get("method"), msg.get("params"),
                                     msg.get("sessionId")))
        except Exception:
            self.events.put(("_closed", {}, None))

    def send(self, method: str, params: dict | None = None,
             session_id: str | None = None, timeout: float = 20.0):
        with self._lock:
            self._nid += 1
            mid = self._nid
            box: list = []
            self._pending[mid] = box
        msg = {"id": mid, "method": method, "params": params or {}}
        if session_id:
            msg["sessionId"] = session_id
        self.ws.send(json.dumps(msg))
        t0 = time.time()
        while not box and time.time() - t0 < timeout:
            time.sleep(0.005)
        self._pending.pop(mid, None)
        if not box:
            raise TimeoutError(f"{method} timed out")
        r = box[0]
        if "error" in r:
            raise RuntimeError(f"{method}: {r['error'].get('message')}")
        return r.get("result", {})

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
