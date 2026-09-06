#!/usr/bin/env python3
"""Portable FLUX.2-klein test runner for an unsloth studio images API.

Usage:
  REMOTE_UNSLOTH_URL=http://<box>:8888 REMOTE_UNSLOTH_KEY=<key> \
    python3 run_matrix.py tests-v2.json --out ./results [--only t1_camera_angle,t6_clothing_dressup]

Env:
  REMOTE_UNSLOTH_URL   base URL of the unsloth studio (no trailing slash)
  REMOTE_UNSLOTH_KEY   API key for that studio (Bearer)

Test-definition JSON schema (list):
  { "test": name, "prompt": str, "width": int, "height": int, "seed": int,
    "init_image": path-or-URL (optional; the base image to edit),
    "reference_images": [paths] (optional; extra references, klein <=4),
    "strength": 0.7 }

Notes (verified 2026-09-06):
  - klein is guidance-distilled: no negative prompts; phrase positively.
  - Edits on a 10GB card cap around ~960x544 working memory; upscale after.
  - width/height must be multiples of 16. `upscale` param unsupported for klein.
  - Sequential calls only; one active model per studio (auto-eviction).
"""
import argparse, base64, json, mimetypes, os, sys, time, urllib.request

def b64(p):
    if p.startswith(("http://", "https://")):
        return p  # some backends accept URLs; unsloth wants data-URLs — fetch below
    data = open(p, "rb").read()
    mime = mimetypes.guess_type(p)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(data).decode()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tests")
    ap.add_argument("--out", default="./results")
    ap.add_argument("--only", default="", help="comma-separated test names to run")
    a = ap.parse_args()
    B = os.environ["REMOTE_UNSLOTH_URL"].rstrip("/")
    KEY = os.environ["REMOTE_UNSLOTH_KEY"]

    def post(path, body):
        req = urllib.request.Request(B + path, data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.load(r)

    def get(path):
        req = urllib.request.Request(B + path, headers={"Authorization": "Bearer " + KEY})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    only = {x.strip() for x in a.only.split(",") if x.strip()}
    manifest = []
    for t in json.load(open(a.tests)):
        if only and t["test"] not in only:
            continue
        d = os.path.join(a.out, t["test"])
        os.makedirs(d, exist_ok=True)
        body = {"prompt": t["prompt"], "width": t.get("width", 960), "height": t.get("height", 544), "seed": t.get("seed", 42)}
        if t.get("init_image"):
            body["init_image"] = b64(t["init_image"])
        if t.get("reference_images"):
            body["reference_images"] = [b64(x) for x in t["reference_images"]]
        if t.get("init_image") or t.get("reference_images"):
            body["strength"] = t.get("strength", 0.7)
        try:
            t0 = time.time()
            r = post("/api/inference/images/generate", body)
            gid = r["images"][0]["id"]
            open(os.path.join(d, "out.png"), "wb").write(get(f"/api/inference/images/gallery/{gid}/file"))
            row = {"test": t["test"], "id": gid, "s": round(time.time() - t0, 1)}
            print(f"{t['test']} OK {row['s']}s", flush=True)
        except Exception as e:
            row = {"test": t["test"], "error": str(e)[:300]}
            print(f"{t['test']} FAIL {str(e)[:200]}", flush=True)
        manifest.append(row)
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    ok = sum(1 for m in manifest if m.get("id"))
    print(f"DONE: {ok}/{len(manifest)}", flush=True)

if __name__ == "__main__":
    main()
