#!/usr/bin/env python3
"""Step 5: consolidate verified onsets into the canonical scenes.json (machine-consumable).

Usage: consolidate.py <out_dir> --legacy legacy_scenes.json --checks check_*.json
        --manifest cand_manifest.json [--speakers speakers.json]
        [--supersede old=new,...] [--start-desc "scene 0 description"] [--prefix scene]
Reads:  <out_dir>/pkt_pts.csv, <out_dir>/transcript.json
Writes: <out_dir>/scenes.json

Canonical schema (sequential scene cuts; start split into time + frame; dialogue split
into timing / speaker / on-screen flag / text):
{
  "video": {duration_s, n_frames, avg_fps},
  "transcript": "transcript.json",
  "scene_count": N, "avg_duration_s": X,
  "scenes": [
    {"scene": int, "start_time": "MM:SS.mmm", "start_s": float, "start_frame": int,
     "duration_s": float, "desc": str, "first_frame": "frames/scene_NN.png",
     "dialogue": [{"start_time": "MM:SS.mmm", "start_s": float, "end_s": float,
                   "speaker": str, "on_screen": bool|null, "confidence": "high|inferred|uncertain",
                   "text": str, "continues"?: true, "source_scene"?: int}] }
  ],
  "corrections": {...}, "excluded_false_positives": [...]
}
Onsets = legacy onsets + PASS candidates; --supersede replaces frames (e.g. 3021=3004).
speakers.json: [{"t": 4.65, "speaker": "Thor", "on_screen": true, "confidence": "high"}]
matched to line starts within 0.3 s (whisper emits no labels — attribution is inferred).
A line ending after its scene's end point gets an explicit continuation entry in the
next scene (on_screen null — the next shot usually shows the listener).
"""
import argparse, json, os

def mmss(t): return f"{int(t//60):02d}:{t%60:06.3f}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--legacy", required=True)
    ap.add_argument("--checks", nargs="+", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--speakers", default="")
    ap.add_argument("--supersede", default="")
    ap.add_argument("--start-desc", default="video start")
    ap.add_argument("--prefix", default="scene")
    a = ap.parse_args()
    def locate(name):
        # v2: canonical layout keeps intermediates in <out_dir>/data/; fall back to root (v1).
        for cand in (os.path.join(a.out_dir,"data",name), os.path.join(a.out_dir,name)):
            if os.path.exists(cand): return cand
        return os.path.join(a.out_dir,name)
    pts = [float(l.strip().rstrip(",")) for l in open(locate("pkt_pts.csv")) if l.strip()]
    n = len(pts)
    leg = json.load(open(a.legacy))
    onsets = [sc["start_frame"] for sc in leg["scenes"]]
    desc = {sc["start_frame"]: sc.get("shot_desc_after") or sc.get("desc","") for sc in leg["scenes"]}
    corrections = {}
    for pair in a.supersede.split(","):
        if not pair.strip(): continue
        old, new = (int(x) for x in pair.split("="))
        onsets = [f for f in onsets if f != old]
        if new not in onsets:
            onsets.append(new)
        desc[new] = desc.get(old, "")
        corrections[f"S{new}_onset"] = f"{old} -> {new} (superseded)"
    man = {m["i"]: m for m in json.load(open(a.manifest))}
    verdicts = []
    for fn in a.checks:
        verdicts += json.load(open(fn))
    spk = {}
    if a.speakers:
        spk = {round(s["t"],2): (s["speaker"], s.get("on_screen"), s.get("confidence","inferred"))
               for s in json.load(open(a.speakers))}
    def find_spk(t):
        if not spk: return None   # v2: no speakers map -> dialogue stays "unknown/uncertain", no crash
        if round(t,2) in spk: return spk[round(t,2)]
        best = min(spk, key=lambda x: abs(x-t))
        return spk[best] if abs(best-t) < 0.3 else None

    newdesc = {}
    fails = []
    for e in verdicts:
        m = man[e["i"]]
        if e["verdict"] == "PASS":
            if any(abs(f - m["frame"]) <= 15 for f in onsets if f != m["frame"]):
                print(f"  NOTE: candidate f{m['frame']} within 15f of an existing onset — check --supersede")
            onsets.append(m["frame"])
            newdesc[m["frame"]] = e.get("after_desc","")
        else:
            fails.append({"frame": m["frame"], "t": mmss(pts[m["frame"]]), "note": e.get("note","")})
    onsets = sorted(set(onsets))
    segs = [(s["start"], s["end"], (s.get("text") or "").strip())
            for s in json.load(open(locate("transcript.json")))["segments"]]

    scenes, used_all = [], set()
    for i, f in enumerate(onsets):
        ef = onsets[i+1]-1 if i+1 < len(onsets) else n-1
        sp, ep = pts[f], pts[ef]
        dl, used = [], set()
        for j, (t, te, tx) in enumerate(segs):
            if sp <= t < ep:
                used.add(j)
                hit = find_spk(t)
                spk_name, ons, conf = hit if hit else ("unknown", False, "uncertain")
                dl.append({"start_time": mmss(t), "start_s": round(t,3), "end_s": round(te,3),
                           "speaker": spk_name, "on_screen": ons, "confidence": conf, "text": tx})
        used_all |= used
        d = a.start_desc if f == 0 else newdesc.get(f) or desc.get(f, "")
        scenes.append({"scene": i, "start_time": mmss(sp), "start_s": round(sp,3),
                       "start_frame": f, "duration_s": round(ep-sp,3), "desc": d,
                       "first_frame": f"frames/{a.prefix}_{i:02d}.png", "dialogue": dl,
                       "_end_pts": ep})
    # continuation pass (cut lands mid-line)
    for i in range(len(scenes)-1):
        ep = scenes[i]["_end_pts"]
        for dl in scenes[i]["dialogue"]:
            if dl["end_s"] > ep + 0.02:
                scenes[i+1]["dialogue"].insert(0, {
                    "continues": True, "source_scene": scenes[i]["scene"],
                    "start_time": scenes[i+1]["start_time"], "start_s": scenes[i+1]["start_s"],
                    "end_s": dl["end_s"], "speaker": dl["speaker"], "on_screen": None,
                    "confidence": "high",
                    "text": f"(continuation of scene {scenes[i]['scene']} line {dl['start_time']} — ends {mmss(dl['end_s'])})"})
    for s in scenes: del s["_end_pts"]
    out = {"video": {"duration_s": pts[-1], "n_frames": n, "avg_fps": round(n/pts[-1],2)},
           "transcript": "transcript.json", "scene_count": len(scenes),
           "avg_duration_s": round(pts[-1]/len(scenes),3), "scenes": scenes,
           "corrections": corrections, "excluded_false_positives": fails}
    json.dump(out, open(os.path.join(a.out_dir,"scenes.json"),"w"), indent=1)
    # v2: emit the onset list for step 6 (extract_frames.py) as a JSON array in data/onsets.txt
    onsets_path = os.path.join(a.out_dir,"data","onsets.txt")
    os.makedirs(os.path.dirname(onsets_path), exist_ok=True)
    json.dump([s["start_frame"] for s in scenes], open(onsets_path,"w"))
    cued = sum(len(s["dialogue"]) for s in scenes)
    print(f"scenes.json written: {len(scenes)} scenes, {cued} dialogue entries / {len(segs)} segments")
    unmatched = [i for i in range(len(segs)) if i not in used_all]
    if unmatched: print("UNCUED segments:", [segs[i][2][:40] for i in unmatched])

if __name__ == "__main__":
    main()
