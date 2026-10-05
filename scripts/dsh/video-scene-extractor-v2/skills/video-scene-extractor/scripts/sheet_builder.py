#!/usr/bin/env python3
"""Step 3: extract before/after frames (single select pass) and build 2x2 verification sheets.

Usage: sheet_builder.py <video> <out_dir> <cand_manifest.json>
       [--cell 560x315] [--per-sheet 4] [--offset 8]
Writes: <out_dir>/ext_*.png (0-based after rename), sheet_XX.png, sheet_map.json, cand_ext_map.json
Sheet cell: 34px label bar (c## f#### MM:SS.mmm MAD=##) + BEFORE(f-off) | AFTER(f+off) side by side.
NO -frames:v (truncates the select). Output starts at 1 -> shifted to 0-based immediately.
"""
import argparse, json, os, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont

def font(sz=18):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("out_dir"); ap.add_argument("manifest")
    ap.add_argument("--cell", default="560x315")
    ap.add_argument("--per-sheet", type=int, default=4)
    ap.add_argument("--offset", type=int, default=8)
    a = ap.parse_args()
    cw, ch = (int(x) for x in a.cell.split("x"))
    man = json.load(open(a.manifest))
    ext = []  # (file_order_idx0, cand_i, side)
    for m in man:
        ext.append((m["i"], "b", m["frame"]-a.offset))
        ext.append((m["i"], "a", m["frame"]+a.offset))
    frames = [e[2] for e in ext]
    sel = "+".join(f"eq(n,{f})" for f in frames)
    r = subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",a.video,
                        "-vf",f"select='{sel}'","-vsync","vfr","-q:v","2",
                        os.path.join(a.out_dir,"x_%03d.png")], capture_output=True, text=True)
    if r.returncode != 0 or len(frames) != len([f for f in os.listdir(a.out_dir) if f.startswith("x_")]):
        raise SystemExit(f"extraction failed or count mismatch: {r.stderr[-500:]}")
    # shift rename 1-based -> 0-based
    for i in range(len(frames)):
        s = os.path.join(a.out_dir, f"x_{i+1:03d}.png")
        d = os.path.join(a.out_dir, f"ext_{i:03d}.png")
        os.replace(s, d)
    ext_map = {}
    for i, (ci, side, f) in enumerate(ext):
        ext_map[f"ext_{i:03d}.png"] = {"i": ci, "side": side, "frame": f}
    json.dump(ext_map, open(os.path.join(a.out_dir,"cand_ext_map.json"),"w"), indent=1)

    fnt = font()
    bar = 34
    # 2 candidates per row x 2 rows (a 4-candidate batch): each candidate owns a
    # 2*cw-wide row holding BEFORE | AFTER. (Old layout W=2*cw, H=2*(ch+bar)
    # with one candidate per row silently rendered slots 2-3 of a 4-batch
    # OFF-CANVAS while sheet_map.json still listed them.)
    W = 4*cw; H = 2*(ch+bar)
    sheet_map = {}
    for s in range(0, len(man), a.per_sheet):
        batch = man[s:s+a.per_sheet]
        img = Image.new("RGB", (W, H), (10,10,10))
        dr = ImageDraw.Draw(img)
        for slot, m in enumerate(batch):
            row, half = divmod(slot, 2)
            y = row*(ch+bar)
            x0 = half*(2*cw)
            dr.rectangle([x0, y, x0+2*cw, y+bar], fill=(0,0,0))
            dr.text((x0+4, y+4), f"c{m['i']:02d} f{m['frame']:05d} {m['mmss']} MAD={m['mad']}",
                    font=fnt, fill=(255,220,80))
            for col, side in enumerate(("b","a")):
                x = x0 + col*cw
                key = [k for k,v in ext_map.items() if v["i"]==m["i"] and v["side"]==side][0]
                im = Image.open(os.path.join(a.out_dir, key)).resize((cw, ch))
                img.paste(im, (x, y+bar))
        name = f"sheet_{s//a.per_sheet:02d}.png"
        img.save(os.path.join(a.out_dir, name))
        sheet_map[name] = [m["i"] for m in batch]
    json.dump(sheet_map, open(os.path.join(a.out_dir,"sheet_map.json"),"w"), indent=1)
    n_sheets = (len(man)+a.per_sheet-1)//a.per_sheet
    print(f"extracted {len(ext)} frames, built {n_sheets} sheets "
          f"({W}x{H}); sheet_00..sheet_{n_sheets-1:02d}.png")

if __name__ == "__main__":
    main()
