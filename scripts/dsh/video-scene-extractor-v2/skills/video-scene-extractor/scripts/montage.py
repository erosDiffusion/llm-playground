#!/usr/bin/env python3
"""Step 7: spot-verification montages from scenes_final.json + frames dir.

Usage: montage.py <frames_dir> <scenes_final.json> <out_prefix> [--cols 5] [--cell 320x180]
Cells 320x180 + 26px label bar (S## | MM:SS.mmm | f####); 5 columns; splits into
~1.2MP images (montage_out_a.png, _b.png, ...). Keep each montage <= ~1.2MP for the
NInfer vision budget (~4.7k patches each).
"""
import argparse, json, os
from PIL import Image, ImageDraw, ImageFont

def font(sz=17):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames_dir"); ap.add_argument("scenes"); ap.add_argument("out_prefix")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--cell", default="320x180")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out_prefix) or ".", exist_ok=True)  # v2: out dir must not pre-exist
    cw, ch = (int(x) for x in a.cell.split("x"))
    lb = 26
    scenes = json.load(open(a.scenes))["scenes"]
    fnt = font()
    per_sheet_cols = a.cols
    rows_per = int(1_200_000 // (per_sheet_cols*cw*(ch+lb)))  # ~1.2MP per image
    idx = ord("a"); k = 0
    while k < len(scenes):
        chunk = scenes[k:k+per_sheet_cols*rows_per]
        rows = (len(chunk)+per_sheet_cols-1)//per_sheet_cols
        img = Image.new("RGB", (per_sheet_cols*cw, rows*(ch+lb)), (10,10,10))
        dr = ImageDraw.Draw(img)
        for j, s in enumerate(chunk):
            # canonical schema (consolidate.py): scene/start_time; legacy: n/start_mmss
            n = s.get("n", s.get("scene"))
            tc = s.get("start_mmss", s.get("start_time"))
            r, c = divmod(j, per_sheet_cols)
            x, y = c*cw, r*(ch+lb)
            dr.rectangle([x, y, x+cw, y+lb], fill=(0,0,0))
            dr.text((x+4, y+3), f"S{n:02d} | {tc} | f{s['start_frame']}",
                    font=fnt, fill=(255,220,80))
            im = Image.open(os.path.join(a.frames_dir, f"scene_{n:02d}.png")).resize((cw, ch))
            img.paste(im, (x, y+lb))
        out = f"{a.out_prefix}_{chr(idx)}.png"
        img.save(out)
        n0 = chunk[0].get("n", chunk[0].get("scene")); n1 = chunk[-1].get("n", chunk[-1].get("scene"))
        print(out, img.size, f"scenes S{n0:02d}-S{n1:02d}")
        k += len(chunk); idx += 1

if __name__ == "__main__":
    main()
