#!/usr/bin/env python3
"""trackprobe: list every media track (audio + subtitle) this Prime title
streams, by decoding the base64 track descriptors embedded in CDN segment URLs.
Read-only Network domain (no Runtime, no page writes).
Usage: trackprobe.py [seconds]   (keep the video PLAYING)"""
from __future__ import annotations

import base64
import re
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_net import CDPNet

SEC = int(sys.argv[1]) if len(sys.argv) > 1 else 45
B64_RE = re.compile(r"[A-Za-z0-9+/_=-]{16,}")
LANG_RE = re.compile(r"\b([a-z]{2}[-_][A-Z]{2})\b")
CDN_RE = re.compile(r"(pv-cdn\.net|media-amazon|dm/|cmaf|dash|ism|manifest|\.mpd|\.m3u8)", re.I)


def try_b64(tok: str) -> str:
    pad = "=" * (-len(tok) % 4)
    try:
        raw = base64.urlsafe_b64decode(tok + pad)
    except Exception:
        return ""
    return raw.decode("latin-1", "replace")


def main():
    c = CDPNet(9222)
    targets = c.send("Target.getTargets")["targetInfos"]
    t = next(t for t in targets
             if t.get("type") == "page" and "primevideo" in t.get("url", ""))
    sid = c.send("Target.attachToTarget",
                 {"targetId": t["targetId"], "flatten": True})["sessionId"]
    c.send("Network.enable", {}, session_id=sid)
    print(f"attached {t['targetId'][:8]} — watching CDN traffic {SEC}s "
          f"(keep playing; consent dialog may pop -> Allow)")

    tracks: dict[str, int] = {}      # descriptor text -> count
    hosts: dict[str, int] = {}
    t0 = time.time()
    while time.time() - t0 < SEC:
        try:
            method, params, sess = c.events.get(timeout=1.0)
        except Exception:
            continue
        if sess != sid or method != "Network.requestWillBeSent":
            continue
        url = params.get("request", {}).get("url", "")
        if not CDN_RE.search(url):
            continue
        host = url.split("/")[2] if "://" in url else "?"
        hosts[host] = hosts.get(host, 0) + 1
        for tok in B64_RE.findall(url.split("?")[0].split("/")[-1]):
            dec = try_b64(tok)
            langs = LANG_RE.findall(dec)
            if langs:
                key = ",".join(sorted(set(langs))) + " | " + \
                      re.sub(r"[^\x20-\x7e]", ".", dec)[:60]
                tracks[key] = tracks.get(key, 0) + 1

    print("\n--- hosts seen ---")
    for h, n in sorted(hosts.items(), key=lambda x: -x[1])[:6]:
        print(f"  {n:4}  {h}")
    print("\n--- decoded track descriptors ---")
    for k, n in sorted(tracks.items(), key=lambda x: -x[1]):
        print(f"  x{n:<4} {k}")
    if not tracks:
        print("  (no base64 lang descriptors found in URLs this window — "
              "the manifest may only load on a fresh start; seek/restart the title)")
    c.close()


if __name__ == "__main__":
    main()
