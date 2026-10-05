#!/usr/bin/env python3
"""Step 0+2: probe packet grid, compute MAD signal, emit isolated-spike candidates.

Usage: mad_scan.py <video> <out_dir> [--min1 35] [--quiet1 14] [--min2 20] [--quiet2 30]
                 [--cluster 12] [--exclude f1,f2,..] [--quiet]
Writes: <out_dir>/data/pkt_pts.csv, data/mad.json, data/cand_manifest.json, data/candidates.txt
v2: intermediates live in <out_dir>/data/ (canonical step-8 layout; the runbook's edge-case
    check reads data/cand_manifest.json); --quiet prints only the summary lines.
Semantics: mad[k] = mean-abs-diff(frame k -> k+1); spike at k => new shot starts at k+1.
Two tiers (union, tier tagged): tier1 = mad[k]>=MIN1, both neighbors <=QUIET1 (hard cuts);
tier2 = mad[k]>=MIN2, both neighbors <=QUIET2 (cut trains / action cuts).
12-frame clustering (keep max per cluster).
"""
import argparse, json, subprocess, os, csv

def pts_list(video):
    r = subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
                        "-show_entries","packet=pts_time","-of","csv=p=0", video],
                       capture_output=True, text=True, check=True)
    return [float(l) for l in r.stdout.split() if l]

def mad(video, out):
    r = subprocess.run(
        ["ffmpeg","-hide_banner","-i",video,
         "-vf","scale=320:180","-fps_mode","passthrough","-f","rawvideo","-pix_fmt","gray","pipe:1"],
        capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed: {r.stderr.decode()[-500:]}")
    raw = r.stdout
    n = len(raw)//(320*180)
    vals = []
    for i in range(n-1):
        a, b = raw[i*57600:(i+1)*57600], raw[(i+1)*57600:(i+2)*57600]
        s = sum(abs(x-y) for x, y in zip(a, b))
        vals.append(s/57600)
    json.dump(vals, open(out,"w"))
    return vals

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("out_dir")
    ap.add_argument("--min1", type=float, default=35.0)
    ap.add_argument("--quiet1", type=float, default=14.0)
    ap.add_argument("--min2", type=float, default=20.0)
    ap.add_argument("--quiet2", type=float, default=30.0)
    ap.add_argument("--cluster", type=int, default=12)
    ap.add_argument("--exclude", default="", help="comma-separated frame indices already known onsets")
    ap.add_argument("--quiet", action="store_true", help="summary lines only")
    a = ap.parse_args()
    dat = os.path.join(a.out_dir, "data")
    os.makedirs(dat, exist_ok=True)

    pts = pts_list(a.video)
    with open(os.path.join(dat,"pkt_pts.csv"),"w") as f:
        for p in pts: f.write(f"{p}\n")
    madv = mad(a.video, os.path.join(dat,"mad.json"))

    excl = {int(x) for x in a.exclude.split(",") if x.strip()}
    cand, seen = [], set()
    for k in range(1, len(madv)-1):
        n1, n2 = madv[k-1], madv[k+1]
        tier = 0
        if madv[k] >= a.min1 and n1 <= a.quiet1 and n2 <= a.quiet1: tier = 1
        elif madv[k] >= a.min2 and n1 <= a.quiet2 and n2 <= a.quiet2: tier = 2
        if tier and k not in seen:
            seen.add(k)
            cand.append({"k": k, "mad": round(madv[k],1), "tier": tier})
    # cluster: keep max per cluster of CLUSTER frames; onset frame = k+1
    cand.sort(key=lambda c: c["k"])
    clusters, cur = [], []
    for c in cand:
        if cur and c["k"] - cur[-1]["k"] > a.cluster:
            clusters.append(cur); cur = []
        cur.append(c)
    if cur: clusters.append(cur)
    best = [max(cl, key=lambda c: c["mad"]) for cl in clusters]
    onsets = [c["k"]+1 for c in best
              if c["k"]+1 not in excl and c["k"]+1 < len(pts)]
    man = [{"i": i, "frame": f, "t": round(pts[f],3),
            "mmss": f"{int(pts[f]//60):02d}:{pts[f]%60:06.3f}",
            "mad": round(madv[f-1],1), "tier": next(c["tier"] for c in best if c["k"]+1==f),
            "before_frame": f-8, "after_frame": f+8}
           for i, f in enumerate(onsets)]
    json.dump(man, open(os.path.join(dat,"cand_manifest.json"),"w"), indent=1)
    open(os.path.join(dat,"candidates.txt"),"w").write("\n".join(map(str,onsets)))
    print(f"frames={len(pts)}  last_pts={pts[-1]:.3f}  avg_fps={len(pts)/pts[-1]:.2f}")
    print(f"spikes: tier1 {sum(1 for c in cand if c['tier']==1)} + tier2 {sum(1 for c in cand if c['tier']==2)} "
          f"-> clusters {len(clusters)} -> candidates {len(man)} (excluded {len(excl)})")
    print("onsets:", ", ".join(map(str, onsets)))

if __name__ == "__main__":
    main()
