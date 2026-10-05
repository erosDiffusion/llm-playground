#!/usr/bin/env python3
"""Frame identity / difference spot-check (arbitration tool) + start-frame verification.

Usage: hashcheck.py <a.png> <b.png>
Resizes both to 64x36 gray; prints md5 of each and mean|delta|. mean|delta| == 0.00
means pixel-identical at that scale (same frame). Use to arbitrate disputed
montage cells / extraction results: re-extract one frame independently and compare.

Usage (v2): hashcheck.py <video> <frames_dir> <scenes.json>
Step-6 verification protocol, fully deterministic: loads the raw gray pipe
(scale=320:180, -fps_mode passthrough = index space of truth), joins each scene's
start_frame FROM scenes.json (never hand-typed), compares frames/scene_NN.png
(resized 320x180 gray) against that raw frame. Decision: mean|delta| <= 6 = MATCH
(same-frame q:v-PNG vs raw baseline is 1.0-1.8, NOT 0.00; different shots run 20-70).
Exit code 1 on any MISMATCH.
"""
import sys, hashlib, json, os, subprocess
from PIL import Image

def g64(p):
    im = Image.open(p).convert("L").resize((64,36))
    return im.tobytes()

def pair(a_path, b_path):
    a, b = g64(a_path), g64(b_path)
    ma = sum(abs(x-y) for x,y in zip(a,b))/len(a)
    print(f"{a_path}: md5={hashlib.md5(a).hexdigest()[:12]}")
    print(f"{b_path}: md5={hashlib.md5(b).hexdigest()[:12]}")
    print(f"mean|delta| = {ma:.2f}  ({'IDENTICAL' if ma < 0.005 else 'different'})")

def verify(video, frames_dir, scenes_path):
    W, H = 320, 180
    r = subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",video,
                        "-vf",f"scale={W}:{H}","-fps_mode","passthrough",
                        "-f","rawvideo","-pix_fmt","gray","pipe:1"], capture_output=True, check=True)
    raw, fs, ok = r.stdout, W*H, True
    scenes = json.load(open(scenes_path))["scenes"]
    for s in scenes:
        f = s["start_frame"]                      # join FROM scenes.json (catalog rule 16)
        png = os.path.join(frames_dir, os.path.basename(s["first_frame"]))
        im = Image.open(png).convert("L").resize((W,H)).tobytes()
        rawf = raw[f*fs:(f+1)*fs]
        if len(rawf) != fs:
            print(f"{s['first_frame']}: start_frame={f} OUT OF RANGE (raw frames={len(raw)//fs}) -> MISMATCH"); ok = False; continue
        d = sum(abs(x-y) for x,y in zip(im,rawf))/fs
        m = "MATCH" if d <= 6 else "MISMATCH"
        if d > 6: ok = False
        print(f"{s['first_frame']}: start_frame={f} mean|delta|={d:.2f} -> {m}")
    print(f"verified {len(scenes)} start frames against raw pipe: {'ALL MATCH' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    if len(sys.argv) == 3:
        pair(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 4:
        verify(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        raise SystemExit("usage: hashcheck.py <a.png> <b.png>  |  hashcheck.py <video> <frames_dir> <scenes.json>")
