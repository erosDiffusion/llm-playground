#!/usr/bin/env python3
"""Network discovery probe: watch what subtitle/media files the Prime tab fetches.

Run this, then press play on the Prime tab. Prints every promising request and
samples the body of anything that looks like subtitles (vtt/ttml/dfxp).
Usage: netprobe.py [seconds]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_net import CDPNet

SEC = int(sys.argv[1]) if len(sys.argv) > 1 else 60
URL_RE = re.compile(r"(vtt|ttml|dfxp|subtitle|caption|cue|cc_|_cc|text_)", re.I)
MEDIA_RE = re.compile(r"(\.m4s|\.m3u8|dash|mpd|segment|Segment|isoff|media[/_])", re.I)
BODY_MIMES = re.compile(r"(vtt|ttml|dfxp|dash|xml|json|text/plain)", re.I)


def main():
    c = CDPNet(9222)
    targets = c.send("Target.getTargets")["targetInfos"]
    t = next(t for t in targets
             if t.get("type") == "page" and "primevideo" in t.get("url", ""))
    sid = c.send("Target.attachToTarget",
                 {"targetId": t["targetId"], "flatten": True})["sessionId"]
    c.send("Network.enable", {}, session_id=sid)
    print(f"attached {t['targetId'][:8]} — Network only (no Runtime). "
          f"Press PLAY on the Prime tab now. Watching {SEC}s…")

    want_body: dict[str, str] = {}
    seen_media: list[str] = []
    t0 = time.time()
    while time.time() - t0 < SEC:
        try:
            method, params, sess = c.events.get(timeout=1.0)
        except Exception:
            continue
        if sess != sid or method not in ("Network.responseReceived",
                                         "Network.requestWillBeSent"):
            continue
        r = params.get("response") if method == "Network.responseReceived" else None
        url = (r or params.get("request", {})).get("url", "")
        mime = (r or {}).get("mimeType", "")
        if URL_RE.search(url) or BODY_MIMES.search(mime):
            rid = params["requestId"]
            print(f"[sub/manifest] {mime or '?':24} {url[:130]}")
            if r and len(want_body) < 10:
                want_body[rid] = url
        elif MEDIA_RE.search(url) and len(seen_media) < 12:
            seen_media.append(url[:130])
            print(f"[media] {url[:130]}")

    print("\n--- sampling response bodies ---")
    for rid, url in want_body.items():
        try:
            res = c.send("Network.getResponseBody", {"requestId": rid}, session_id=sid)
            body = res.get("body", "")
            enc = res.get("base64Encoded", False)
            if enc:
                import base64
                body = base64.b64decode(body).decode("utf-8", "replace")
            print(f"\n=== {url[:120]} ===\n{body[:600]}")
        except Exception as e:
            print(f"body fetch failed for {url[:80]}: {e}")
    c.close()


if __name__ == "__main__":
    main()
