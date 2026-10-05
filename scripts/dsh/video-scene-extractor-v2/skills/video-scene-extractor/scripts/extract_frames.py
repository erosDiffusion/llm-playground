#!/usr/bin/env python3
"""Step 6: extract the start frame of every scene in ONE select pass, 0-based.

Usage: extract_frames.py <video> <frames_dir> <onset_list.json|txt>
onset list: JSON array of frame indices, or a text file with one index per line / space-separated.
Contract: single select + -vsync vfr (NO -frames:v), x_%03d.png, shift-rename to 0-based scene_NN.png.
"""
import argparse, json, os, subprocess, re

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("frames_dir"); ap.add_argument("onsets")
    a = ap.parse_args()
    raw = open(a.onsets).read()
    try:
        v = json.loads(raw)
        # v2 fix: a bare number ("0") parses as int, not list -> TypeError escaped the except.
        frames = [int(f) for f in (v if isinstance(v, list) else [v])]
    except json.JSONDecodeError:
        frames = [int(x) for x in re.findall(r"\d+", raw)]
    os.makedirs(a.frames_dir, exist_ok=True)
    sel = "+".join(f"eq(n,{f})" for f in frames)
    r = subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",a.video,
                        "-vf",f"select='{sel}'","-vsync","vfr","-q:v","2",
                        os.path.join(a.frames_dir,"x_%03d.png")], capture_output=True, text=True)
    got = len([f for f in os.listdir(a.frames_dir) if f.startswith("x_")])
    if r.returncode != 0 or got != len(frames):
        raise SystemExit(f"extraction failed or count mismatch ({got}/{len(frames)}): {r.stderr[-500:]}")
    for i in range(len(frames)):
        os.replace(os.path.join(a.frames_dir,f"x_{i+1:03d}.png"),
                   os.path.join(a.frames_dir,f"scene_{i:02d}.png"))
    print(f"extracted {len(frames)} start frames -> scene_00..scene_{len(frames)-1:02d}.png (0-based)")

if __name__ == "__main__":
    main()
