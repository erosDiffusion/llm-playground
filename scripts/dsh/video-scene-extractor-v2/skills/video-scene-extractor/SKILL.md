# video-scene-extractor — runbook

## v2 changes (2026-10-05, from a live run on prn_00389_)

All seven runbook/script mismatches hit during that run are fixed; the invocation block below now runs end-to-end with zero manual intervention:

1. `mad_scan.py`: `--quiet` was in the runbook but argparse rejected it (ambiguous with `--quiet1/--quiet2`) — now a real flag. Intermediates move to `<out_dir>/data/` (matches the runbook's edge-case check and the step-8 canonical layout).
2. `consolidate.py`: reads `data/pkt_pts.csv` (root fallback kept); crashes with `min() iterable argument is empty` when a transcript exists but `--speakers` was not passed — now guarded (dialogue falls back to speaker `unknown`, confidence `uncertain`); also writes `data/onsets.txt` (JSON array) so step 6 runs straight after step 5.
3. `extract_frames.py`: an onsets file containing a bare number (`0`) parsed via `json.loads` to an int and raised `TypeError` (escaped the `JSONDecodeError` fallback) — fixed; JSON array, bare number, and one-per-line all parse.
4. `montage.py`: real signature is `<frames_dir> <scenes.json> <out_prefix>` (the runbook showed a video argument) — runbook corrected; the output directory is now auto-created.
5. `hashcheck.py`: the runbook's step-8 invocation (`<video> frames/ scenes.json`) did not exist — implemented as the deterministic step-6 verification protocol: raw gray pipe (320×180, `-fps_mode passthrough`), `start_frame` joined from `scenes.json`, mean|Δ| ≤ 6 = MATCH (baseline 1.0–1.8), exit 1 on any mismatch. Two-PNG arbitration mode unchanged.
6. `check_ffmpeg.py`: grepped `ffmpeg -h formats` for `-lavfi` — never present, so it failed ffmpeg 6.1.1, the version the skill itself requires, and told users to upgrade a working install. Now tests the filters the pipeline actually uses (`scdet`, `select`, `metadata`, `scale`).
7. scdet metadata format documented wrong (line 2a): actual output is three lines per frame (`frame:` / `lavfi.scd.mafd=` / `lavfi.scd.score=`), `=` separators — the documented two-line `:` shape breaks naive parsers.

## FFmpeg Version Requirements

### Prerequisites Check

Before running the pipeline, verify ffmpeg is installed and compatible:

```bash
# Check version and lavfi support
ffmpeg -version | grep "Lavf"

# Required: ffmpeg 6.1.1+ with lavfi filter support
# If missing or old version, upgrade:
apt-get update && apt-get install -y ffmpeg
# Or via conda:
conda install ffmpeg=6.1.1
```

**Critical:** The skill scripts require `lavfi` filter for `scdet` detection. Without it, the pipeline will fail with "Unrecognized option 'fr'" or similar errors.

## Deterministic Invocation (DO NOT SKIP)

### Prerequisites

**FFmpeg Version Check:**
```bash
# Run this first to verify ffmpeg is compatible
python3 $SKILL/scripts/check_ffmpeg.py

# If lavfi is missing, upgrade:
apt-get update && apt-get install -y ffmpeg
# Or conda:
conda install ffmpeg=6.1.1
```

- Video file path: `<video_path>` (must be accessible, e.g., `h3.video_00001_.mp4`)
- Output directory: `<output_dir>` (will be created automatically)
- Frames directory: `<frames_dir>` (for step 6, separate from output_dir)

### Full Pipeline Execution

```bash
# PATH CONTRACT (never deviate):
#   project root = cwd for the whole run: ~/Apps/generated/<video-basename>/
#   (basename without extension, e.g. MiniMax_H3_00058_); the skill dir is READ-ONLY code,
#   never a write target. <output_dir> = . and <frames_dir> = frames/ under that root.
# DSH_VIDEO_SKILL_DIR is published by the dsh-video-scene-extractor bundle (shell-env).
export SKILL="${DSH_VIDEO_SKILL_DIR:?the dsh-video-scene-extractor bundle is not installed — no DSH_VIDEO_SKILL_DIR in the shell environment}"
mkdir -p ~/Apps/generated/<video-basename> && cd ~/Apps/generated/<video-basename> && pwd

# Step 0+2: probe packets and detect scene candidates
# (v2: writes all intermediates under <output_dir>/data/; --quiet is a real flag now)
python3 $SKILL/scripts/mad_scan.py <video_path> <output_dir> --min1 35.0 --quiet1 14.0 --min2 20.0 --quiet2 30.0 --cluster 12 --quiet

# Edge case handling: if no candidates (static video), create minimal legacy file
if [ ! -f data/cand_manifest.json ] || [ $(cat data/cand_manifest.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))") -eq 0 ]; then
    cat > data/legacy_scenes.json << 'LEGACY'
{"scenes": [{"scene": 0, "start_frame": 0, "shot_desc_after": "", "desc": "video start"}]}
LEGACY
fi

# Step 3: build before/after sheets (only if candidates exist)
if [ -f data/cand_manifest.json ] && [ $(cat data/cand_manifest.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))") -gt 0 ]; then
    python3 $SKILL/scripts/sheet_builder.py <video_path> <output_dir> data/cand_manifest.json
else
    echo "No candidates detected — skipping verification steps (static video)"
fi

# Step 4: verify sheets (user action — write check_*.json for each sheet)
# For static videos with no candidates, create empty checks file
if [ ! -f data/checks.json ]; then
    echo '[]' > data/checks.json
fi

# Step 5: consolidate scenes into canonical JSON
# (v2: reads data/pkt_pts.csv with root fallback; --speakers optional — without it
#  dialogue stays speaker "unknown"/uncertain instead of crashing; writes data/onsets.txt)
python3 $SKILL/scripts/consolidate.py <output_dir> \
    --legacy data/legacy_scenes.json \
    --checks data/checks.json \
    --manifest data/cand_manifest.json \
    --start-desc "video start" \
    --prefix scene

# Step 6: extract start frames (data/onsets.txt comes from step 5; JSON array or plain text both parse)
python3 $SKILL/scripts/extract_frames.py <video_path> <frames_dir> data/onsets.txt

# Step 7: montage verification (optional for static videos)
# (v2: signature is <frames_dir> <scenes.json> <out_prefix>; out dir auto-created)
python3 $SKILL/scripts/montage.py frames/ scenes.json montages/montage

# Step 8: verify every start frame against the raw pipe (step-6 protocol, deterministic;
# joins start_frame from scenes.json, exit 1 on any MISMATCH; Δ<=6 = MATCH, baseline 1.0-1.8)
python3 $SKILL/scripts/hashcheck.py <video_path> frames/ scenes.json
```

### Expected outputs by video type

| Video Type | Scenes Detected | Output Files |
|------------|-----------------|--------------|
| **Static image** (no cuts) | 1 | `scenes.json` (single scene), `frames/scene_00.png`, minimal verification |
| **Cutscene with jumps** | Multiple | Full pipeline: sheets → checks → scenes.json → frames/ → montages/ |
| **Audio-rich video** | With dialogue cues | Includes transcript.json, speaker attribution in scenes.json |

### Quick sanity check after execution
```bash
python3 -c "import json; d=json.load(open('scenes.json')); print(f'Scenes: {d[\"scene_count\"]}, Duration: {d[\"video\"][\"duration_s\"]}s')"
```

## Environment quickstart (deployment notes — machine-specific; skip lines that do not match your machine)

- **Box = brain only.** No rendering on this machine: video renders run on the 5090 box `192.168.1.163:8188` over LAN (no auth, same API). While DSH + unsloth are open here, this box's own ComfyUI is stopped / models freed (user rule) → the 10 GB 3080 is dedicated to the LLM; no park/resume protocol needed here.
- **Project folder:** `generated/<video-basename>/` with the canonical layout (step 8). Copy the source into `<project>/video/` first (self-contained project).
- **Whisper venv (local, GPU):** `~/Progetti/whisper-offload/venv/bin/python` (faster-whisper 1.2.1, large-v3 float16 CUDA, model cache `~/.cache/huggingface`). ~15 s per clip incl. model load. Quality note (measured 2026-10-03, 179 s reference clip): coarser segmentation than pywhisper large-v3 (~90% word overlap) → treat output as DRAFT; sanity-check segment boundaries against audio pts before cueing.
- **ffmpeg version check:** The skill requires ffmpeg 6.1.1 or later with `lavfi` support for `scdet` filter. Run: `ffmpeg -version | grep "Lavf"`. If missing, upgrade using: `apt-get update && apt-get install -y ffmpeg` (system packages) or `conda install ffmpeg=6.1.1` (conda). **If lavfi is unavailable**, the scripts will fail with "Unrecognized option 'fr'" or similar — check that ffmpeg supports `-lavfi` filter.
- **ffmpeg 6.1.1: NO `lavfi` filter** (same build as the 5090 box) — scene-score pass = `scdet` + `metadata=mode=print` (see 2a).
- **CPU:** i9-11900K, 8 cores / 16 threads (whisper `cpu_threads=8` if ever CPU-bound; transcription itself runs CUDA).
- **Vision:** the agent model is a Qwen3.5 VL served by unsloth studio at `http://127.0.0.1:8888/v1` (openai-completions; images travel as data-URL `image_url` parts). No NInfer on this box → the NInfer-specific notes (per-prompt patch budget, decode-400 mpegts bug, server concurrency slots) do NOT apply; keep analysis images ≤1280 px per side as before. Weaker eye than the 5090 box's model → lean on the arbitration fallbacks: single-frame crops ≥420×236 with big labels, 64×36 gray hash compares, and "MAD-confirmed, not visually inspected" flagging when in doubt.
- **File exchange with the 5090 box (192.168.1.163):** SSH key auth both ways, user `oem` (established 2026-10-03; sshd enabled on the 5090 box). Upload: `scp -r <local> oem@192.168.1.163:<remote path>`; download: reverse; use `rsync -av` for large transfers. Render hand-off: `curl -X POST http://192.168.1.163:8188/prompt` (API-format workflow) + poll `http://192.168.1.163:8188/history/<prompt_id>`; outputs via `GET /view?filename=&subfolder=&type=output`. Note: new SaveVideo exposes the mp4 under the `images` key with `animated: true` (not `videos`).

## Pipeline (order matters — verification-first)

```
0 probe        ffprobe packet dump → pkt_pts.csv            (deterministic)
1 transcript   whisper large-v3 → transcript.json          (if not provided)
2 candidates   scene_score pass + isolated-MAD-spike pass   (deterministic)
3 sheets       extract f±8 frames + build before/after sheets (deterministic)
4 verify       view sheets (≤2/turn), write check_*.json    (vision — this is the only vision step)
5 consolidate  merge onsets, cue transcript, write scenes json (deterministic)
6 re-extract   start frames single-pass + 0-based rename     (deterministic)
7 spot-verify  montage of all start frames → view 1–2 times (vision)
8 deliver      scenes.md (list + cue sheet) + verification report
```

Scripts in `scripts/` are self-contained (argparse, stdlib + ffmpeg + PIL):
`mad_scan.py` (steps 0+2), `sheet_builder.py` (3), `consolidate.py` (5), `extract_frames.py` (6), `montage.py` (7), `hashcheck.py` (anywhere).

## Step 0 — probe (NEVER trust the container fps)

```bash
ffprobe -v error -select_streams v:0 -show_entries packet=pts_time -of csv=p=0 in.webm > pkt_pts.csv
```
- VFR video: container `r_frame_rate` (e.g. 359/12) is MISLEADING. Frame index k ↔ pts `pkt_pts.csv` line k. All "times" in the deliverable come from this file.
- Also record: `n_frames`, last pts, avg fps = n_frames / last_pts.
- Start frame of cut at frame f = **the first frame of the NEW shot** (verify by definition in step 7).

## Step 1 — transcript (if not provided)

**1a. Audio map first (cheap, saves wasted transcription):**
```bash
ffprobe -v error -select_streams a:0 -show_entries packet=pts_time -of csv=p=0 in.webm > data/audio_pts.csv
```
Bucket the pts into regions with a gap tolerance (~0.5 s). Captured AI cutscenes often carry audio in only a few windows (measured case: 0–11.8 s + 540.4–542.1 s of a 630 s capture, the rest silent). Extract one 16 kHz mono wav PER REGION (`ffmpeg -ss <start> -t <dur> -i in -ar 16000 -ac 1 region.wav`) and transcribe each, adding the region offset back into the times. If a region is music-only (e.g. a piano rendition — ask/verify with the user), expect zero segments; do not "fix" an empty result by lowering VAD.

**1b. Transcribe** with faster-whisper large-v3 int8 (venv: `~/.venvs/faster-whisper`, see quickstart). Keep `word_timestamps: true`, `condition_on_previous_text=False`, `vad_filter=False`. **No speaker labels exist — all speaker attribution downstream is inferred; mark it as such in the deliverable.**

**1c. Hallucination check (instrumental audio):** on short non-speech blips (outros, music tails) large-v3 routinely hallucinates stock phrases — measured case: "Thanks for watching!" on a 1.7 s piano outro blip with `no_speech_prob = 0.81`. Any line with high `no_speech_prob` on music-only audio is a PROBABLE HALLUCINATION: keep it as a low-confidence cue (`confidence: "uncertain"`), flag it explicitly in scenes.md + the verification report, and never present it as confirmed speech.

**GPU offload (optional, user directive 2026-10-03: delegate if the software is on the box — one task at a time, background job):** a CUDA box with a `faster-whisper` venv (reference: `oem@192.168.1.34:~/Progetti/whisper-offload`, README there) transcribes the same wav in ~15 s (large-v3 float16). Two traps: (1) extract the wav LOCALLY and scp it — no ffmpeg needed on the box for this step; (2) the `av` `metadata_errors` bug → wave-module bypass (see quickstart). **Quality:** measured on the reference clip, faster-whisper output drifts from local pywhisper (22 vs 46 segments, ~90% word overlap, coarser segmentation) → treat box output as a DRAFT; local whisper is canonical. Box ffmpeg frame extraction IS bit-identical (hash-verified) — delegation-safe.

## Step 2 — candidates (two independent passes, then union)

### 2a. scene_score pass (weak alone — use as a net, not a detector)
**Local ffmpeg 6.1.1 has NO `lavfi` filter** — the original command fails. Working substitute (per-frame, index-aligned to the raw/MAD grid):
```bash
ffmpeg -i in.webm -vf "scale=640:360,scdet,metadata=mode=print:file=data/scratch/scdet_meta.txt" -f null -
```
The file holds THREE lines per frame (v2-verified on 6.1.1): `frame:N pts:P pts_time:T`, then `lavfi.scd.mafd=X`, then `lavfi.scd.score=X` — the mafd line sits between, and the separators are `=`, not `:`. Parse the `lavfi.scd.score` key (the key says `scd`, not `scdet`). Index k = frame k on the same grid as `mad.json`.
- Take the top-N scores as review candidates AND use the pass as CORROBORATION: on AI footage every real MAD cut carries a high scdet score (measured: all 29 MAD candidates scored high; max 29.38).
- **Net value (measured):** on AI footage with jump cuts between near-identical framings, MAD can be as low as ~7 (below both tiers) while scdet still flags the cut — one real cut (an 8-frame "AXL" flash) was caught by the net only. Always review the top ~10 scdet scores NOT already in the MAD candidate list.
- **WARNING (older `lavfi`/scene_score variant):** PASS and FAIL score ranges overlap completely → NO usable threshold; candidate *times* offset from true cut frames; metadata `pts` sit on the scaled-OUTPUT timeline, not the packet grid → use frame-indexed lookups only. Measured on the reference video: 24/65 PASS (37%).

### 2b. MAD isolated-spike pass (primary candidate generator)
`scripts/mad_scan.py`:
- Signal: `ffmpeg -i in -vf "scale=320:180" -fps_mode passthrough -f rawvideo -pix_fmt gray pipe:1` → per-frame mean-abs-diff of consecutive frames. **`-fps_mode passthrough` is MANDATORY** (default frame-duplication/dropping removes ~1,000 frames on VFR input and corrupts the index).
- **Semantics: `mad[k]` = change between frame k and k+1. A spike at index k ⇒ the new shot starts at frame k+1.** (Off-by-one here has burned us twice.)
- **Two tiers (run both, take the union, tag the tier):** Tier 1 (hard cuts) `mad[k] ≥ 35`, both neighbors ≤ 14; Tier 2 (net for cut trains / action cuts) `mad[k] ≥ 20`, both neighbors ≤ 30. Then 12-frame clustering (keep the max per cluster). Hard cuts are single-frame events; motion/lightning/fight action drags the neighbor frames.
- Measured on the reference video: 57/62 PASS (92%); all 5 FAILs were in-shot action (pose change, door opening, fight choreography). Tier 1 alone has ~5% false negatives (cut trains with busy neighbors, action cuts at MAD 20–29); Tier 2 adds 4 real cuts + 3 FPs — the visual check resolves all of them. A raw MAD threshold alone is NOT enough; the spike shape narrows it, the ±8-frame visual check (step 4) discriminates.
- **Arbitration rule:** when a legacy/scene_score onset and the MAD spike disagree within ~10 frames, **the MAD spike wins** — the ±8-frame cell granularity cannot resolve a ≤10-frame offset. Settle it with a 2-frame strip (extract both frames side by side, one view) — reference case: scene_score 44.156 → f1543 vs MAD spike 66.0 (neighbors 0.0/5.0) → strip proved f1549 is the cut.
- Content-delta "persistence" tests (±8f/±25f frame-delta comparison) are UNUSABLE on high-motion AI footage: within-shot noise floor p50≈26–39, p99≈42–58 overlaps cut deltas (40–80). Don't build them.

### Union
`cand_manifest.json`: `{i, frame, t, mmss, mad, before_frame: f-8, after_frame: f+8}` for every candidate NOT already a verified onset. Exclude onsets within ~15 frames of each other (keep the max-MAD one).

## Step 3 — before/after sheets (deterministic)

`scripts/sheet_builder.py` (reference geometry, tuned to the vision budget):
- Extract every `before_frame`/`after_frame` in ONE pass: `ffmpeg -i in -vf "select='eq(n,B0)+eq(n,B1)+…'" -vsync vfr -q:v 2 x_%03d.png` — **NO `-frames:v N`** (it truncates the select; the exact select count is enough, ≈150× speed). Output numbering starts at 1 → **shift-rename to 0-based after EVERY batch** (this has burned us every time).
- Sheet = 2×2 grid, each cell = 34 px label bar (`c## f#### MM:SS.mmm MAD=##`) + two 560×315 frames (BEFORE f−8 / AFTER f+8, left/right) → 2284×734 PNG ≈ 6.4k vision patches. DejaVu fonts.
- Write `sheet_map.json` (sheet → candidate indices) + `cand_ext_map.json` (extract file → candidate/side) so verdicts can be written back deterministically.

## Step 4 — verification (the only main-session vision step)

- **NInfer rules (hard):** ≤131,072 raw patches per prompt (1 token = 32×32 px); images are re-sent every turn and compaction evicts them → budget is per-prompt, not session. Keep analysis images ≤1280 px per side when possible. **Never re-view sheets already in context** (costs double).
- **Server contention:** local NInfer typically runs `--max-concurrency 1..2` → **view in the main session, ≤2 sheets per turn, ONE verification pass at a time.** Do not fan out vision subagents (measured: parallel vision subagents fail/time out; also the NInfer decode bug below made them fail silently — diagnose via `~/.dsh/sessions/<session-dir>/<uuid>/session.v4.jsonl.zstd` → `zstd -dc` → `finish` chunk `failure.message`).
- **Vision-400 `media has no decodable video stream`:** known NInfer mpegts misprobe bug on request-image re-encodes. Fix = `ninfer-decode-probe-hint.patch` + rebuild + **server restart** (a running process keeps the binary it started with — check process start time vs binary mtime). If the restart is not possible: retry one sheet per turn (content-dependent, sometimes passes); last resort = accept candidates by isolated-spike signature (92% precision) + hash spot-checks and flag them "MAD-confirmed, not visually inspected" in the report.
- Per sheet: for each cell, BEFORE vs AFTER — a **PASS** (real cut) = different subject framing / camera angle / scene / composition / shot size. A **FAIL** (same shot) = in-shot motion only (pose change, door opening, fight swing, camera drift, lightning). When in doubt: arbitrate with a PIL crop of the exact cell or a single-frame hash compare (64×36 gray md5; mean|Δ|=0.00 = identical) — montage grid reading has swapped adjacent cells 3 times in the reference run.
- Write verdicts IMMEDIATELY after each turn, per batch, to `check_*.json`:
```json
[{"i": 0, "verdict": "PASS|FAIL", "before_desc": "...", "after_desc": "...", "note": "one line"}]
```
`i` = candidate index from the manifest. Do NOT invent other shapes.

## Step 5 — consolidate (deterministic)

`scripts/consolidate.py` writes the **canonical `scenes.json`** (machine-consumable contract):
- onsets = verified legacy onsets + PASS candidate frames (dedupe within 15 frames; record supersessions like 3021→3004 via `--supersede old=new` into a `corrections` block).
- Scene object (start SPLIT into time + frame; dialogue SPLIT into timing / speaker / on-screen flag / text):
```json
{"scene": 0, "start_time": "00:00.000", "start_s": 0.0, "start_frame": 0,
 "duration_s": 4.14, "desc": "one line", "first_frame": "frames/scene_00.png",
 "dialogue": [{"start_time": "00:04.650", "start_s": 4.65, "end_s": 8.59,
               "speaker": "Thor", "on_screen": true, "confidence": "high|inferred|uncertain",
               "text": "…", "continues"?: true, "source_scene"?: 18}]}
```
- Cue transcript: a segment belongs to the FIRST scene whose `[start_pts, end_pts)` contains the segment start (no tolerance — a straddle shows up as a continuation instead).
- **Continuation pass:** a line ending after its scene's end point gets an explicit `continues: true` entry in the next scene (`end_s` = true line end for subtitle/TTS sync; `on_screen: null` — the next shot usually shows the listener). Reference video: 21 of 46 lines span a cut.
- Speakers: whisper emits no labels — pass a `--speakers` map (`[{"t": 4.65, "speaker": "Thor", "on_screen": true, "confidence": "high"}]`, matched within 0.3 s). `confidence` = high (on-screen, unambiguous) / inferred / uncertain. Always carry a top-level `speakers.note` that attribution is inferred.
- Descriptions: for new onsets use the verdict's `after_desc`; for legacy onsets keep the original.
- Top level: `video {duration_s, n_frames, avg_fps}`, `transcript`, `scene_count`, `avg_duration_s`, `scenes[]`, `corrections`, `excluded_false_positives` (FAIL list with frame/time/note).

## Step 6 — re-extract start frames (deterministic)

`scripts/extract_frames.py`: single-pass `select='eq(n,F0)+…'` + `-vsync vfr` (NO `-frames:v`), `x_%03d.png`, then shift-rename to 0-based `scene_NN.png`.

**Verification protocol (do this for EVERY run):**
- **Ground truth = the raw pipe**, not `-ss` seeks: `-ss` time-seeking is ~1 frame off and UNRELIABLE on VFR webm with non-monotonic DTS (measured: seeked frame ≠ target, offsets up to a whole shot). The raw pipe `ffmpeg -i in -vf "scale=320:180" -fps_mode passthrough -f rawvideo -pix_fmt gray pipe:1` is the index space of truth: raw k ↔ packet k ↔ `pkt_pts[k]`.
- Check ALL start frames (not just 3–5): load the raw stream once, and for each scene in `scenes.json` compare `frames/scene_NN.png` (resized 320×180 gray) against **that scene's own `start_frame`** (join from the file — never hand-type indices; a self-inflicted off-by-one once masqueraded as "pipeline drift": scene 24 is f14194, not f14250).
- **Baseline is NOT 0.00:** q:v-2 PNG (full-res, re-encoded) vs raw gray gives mean|Δ| ≈ 1.0–1.8 for the SAME frame (encoding noise; the f233/f250 arb strips and the 31/31 run measured 1.18–1.33). Decision rule: **Δ ≤ 6 = MATCH, Δ > 6 = MISMATCH** (different-shot deltas run 20–70). `hashcheck.py` (md5 + mean|Δ|) is fine for same-path pairs (expect 0.00 there).

## Step 7 — spot-verify montages (vision, ≤2 images)

`scripts/montage.py`: cells 320×180 + 26 px label bar (`S## | MM:SS.mmm | f####`), 5 columns, split into ≤1.2 MP images. Check: (1) each cell shows the START of the new shot (the AFTER side of its cut); (2) no cell swaps (labels vs content); (3) corrections land where expected.

## Step 8 — deliverables (proper folder structure)

```
<project>/
├── video/<name>.webm          # copy of the source (self-contained project)
├── transcript.json
├── scenes.json                # CANONICAL machine-readable output (step-5 schema)
├── scenes.md                  # human cue sheet with scenes table
├── ref2va_prompts.md          # prompt following ref2va template for generation
├── frames/scene_NN.png        # exact start frame per scene (0-based, = scenes[].first_frame)
├── montages/montage_a.png …   # spot-verification montages (labels S##)
├── verification/              # evidence trail: verification-report.md, check_*.json,
│                              #   cand_manifest.json, cand_sheets/, sheet_map.json
└── data/                      # intermediates: pkt_pts.csv, mad.json, scratch/, one-off scripts
```

### Step 8a — `scenes.md` (human cue sheet)

`scenes.md` is a cue sheet, not a data dump. Exact structure (fill every field; no truncation; no placeholder text):

    # Scene list — <video-name>.mp4

    ## References
    | Artifact | Path |
    |---|---|
    | Source video | [video/<name>.mp4](video/<name>.mp4) (<W>×<H>, <fps> fps, <N> frames, <dur> s; source: <absolute source path>) |
    | Canonical scene list (machine-readable) | [scenes.json](scenes.json) |
    | Start frames | [frames/](frames/) |
    | Packet grid (time truth) | [data/pkt_pts.csv](data/pkt_pts.csv) |
    | Candidate evidence (if cuts) | [data/ext_000.png](data/ext_000.png) … [data/cand_manifest.json](data/cand_manifest.json) |

    ## Result
    **<N> scenes, <M> cuts.** <one-sentence summary of the video>

    ## Scene table
    | Scene | Start | Frame | Dur (s) | Shot description | Start frame | Dialogue |
    |---|---|---|---|---|---|---|
    | S00 | 00:00.000 | f0 | 2.21 | <full visual description from the verified frames: subjects, composition, motion> | ![S00](frames/scene_00.png) | <count> or — |

    ## Cut verification   (only if M > 0)
    | # | Cut frame | Time | MAD | Tier | Verdict |
    |---|---|---|---|---|---|
    | c0 | f50 | 00:02.208 | 29.0 | 2 | PASS — <what changes: framing / subject / environment> |

    ## Notes
    - <time source: data/pkt_pts.csv; container fps is approximate>
    - <scene-span semantics, transcript caveats, provenance>

Rules:
- `Shot description` must be written from frames you actually looked at (step-4 verification frames or the exact start frames). NEVER "video start" or any other placeholder.
- Scene span semantics: M cuts → M+1 scenes. Scene i runs from onset[i] to the frame before onset[i+1] (last scene to the final frame). A ±8 candidate window is NOT a scene.
- Times are MM:SS.mmm from `data/pkt_pts.csv` (line k = frame k), never from container fps.
- Every `![S##](frames/scene_NN.png)` link must point at a file that exists (step 6 produces them). Verify before writing.

### Step 8b — `ref2va_prompts.md` (MiniMax-H3 six-section ref2va)

`ref2va_prompts.md` is ONE prompt block in the MiniMax-H3 ref2va six-section format. NOT a YAML dump, NOT per-scene blocks. Reference images by file name (the `frames/` files that get uploaded to the ComfyUI input). Exact shape:

    subject_definitions:

    <Subject 1>: <full appearance: hair, outfit, distinguishing marks>
    <Picture 1>: [Shot 1] first frame — <what the frame shows>
    <Picture 2>: [Shot 2] first frame — <what the frame shows>

    summary:

    [reference generation] <one sentence covering the whole sequence, referencing <Subject N> and <Picture 1> through <Picture N>>

    retention_analysis:

    <Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - <what stays consistent>.
    <Picture 1> ([Shot 1] first frame): fully_preserved - <composition note>.

    detailed_description:

    [Shot 1] <camera + setting + action, ending "matching <Picture 1>".>
    [Shot 2] <…>

    overall_soundscape:

    <diegetic sounds across the sequence>.

    non_diegetic_music:

    N/A   (or the description, if the source clearly has music)

Rules:
- One `<Picture N>` per scene start frame, in scene order; `[Shot N]` numbers are 1-based and match the scene number.
- Subjects appearing in several shots list them: `(appears in [Shot 1], [Shot 3])`.
- `retention_analysis` lines always end `fully_preserved - …` or `partially_preserved - …` (dash + reason).
- Section headers verbatim, no markdown decoration inside the block.

## ABSOLUTE PROHIBITIONS (token & format guard)

1. NEVER embed image or byte data (base64, `data:` URLs, raw binary) in any deliverable, tool call, or chat message. One 512×512 PNG ≈ 400 KB ≈ half a million output tokens: the request is cut at the per-request output limit, the file is left corrupt and the context gets compacted. Reference images by path/filename only.
2. NEVER `cat` or fully read a file bigger than ~200 lines into context when a `head`/`tail` slice suffices — `wc -c` / `wc -l` first.
3. Chat replies stay short (a few sentences). All analysis goes into project files.
4. NEVER write deliverables into the skill directory, `~/Apps/ComfyUI/output/`, or `~/Apps/ComfyUI/input/` (renderer-only domains).
5. Do not invent paths. If a directory does not exist, create it under the project root. After every `cd`, verify with `pwd` — a failed `cd` does not stop the next command in a `&&`-free chain.

## Hard-won catalog (do not rediscover these)

1. `-fps_mode passthrough` or the MAD array is silently wrong (1,041 frames dropped on the reference file).
2. `mad[k]` = change k→k+1; onset = k+1.
3. Container fps lies on VFR; only `pkt_pts.csv` is truth.
4. `-frames:v N` truncates multi-frame `select`; never use it.
5. ffmpeg output numbering starts at 1 → shift-rename after every batch.
6. scene_score: no threshold exists; times offset 0.7–1.5 s (and as little as 6 frames); meta pts on the scaled-output timeline. When MAD and scene_score disagree within ~10 frames, MAD wins (2-frame strip to prove).
7. Content-delta persistence tests don't work on high-motion AI footage.
8. Montage grid reading swaps adjacent cells — arbitrate with PIL crops / hash compares.
9. Large MAD spikes from in-shot action mimic cuts — two-tier isolated-spike shape + visual check.
10. NInfer: per-prompt patch budget (131,072), ≤2 vision turns in parallel, 1–2 server slots, decode-400 = restart the server after a binary fix (in-memory binary ≠ file on disk).
11. Subagent failures are diagnosable: `session.v4.jsonl.zstd` → `finish.failure.message`.
12. Speaker attribution is always inferred (whisper has no labels) — label it in the deliverable.
13. `sheet_builder.py` geometry: 4-candidate batches need a 4*cw × 2*(ch+bar) canvas with slot (row, half) = divmod(slot, 2) and each candidate owning a 2*cw row (BEFORE|AFTER). The old 2*cw-wide canvas silently lost batch slots 2–3 off-canvas while `sheet_map.json` still listed them (fixed in the skill script; a patched copy may exist as `data/scratch/sheet_builder2.py` in old projects).
14. Sheet-grid cells at downscaled view size SWAP/MISREAD (8+ wrong cell identifications in one run — dark flooded-church shots read as "water reflection" instead of "top-down view"). Sheets are leads; for ANY borderline/disputed cell extract the exact frame individually at ≥420×236 with a big label, and cross-check with MAD interval quietness.
15. `-ss` time-seek ≠ frame-accurate on VFR webm (non-monotonic DTS warnings); verify frames against the raw pipe (byte-slice the gray rawvideo), raw k ↔ packet k. Same-frame mean|Δ| baseline ≈ 1.2 (q:v PNG vs raw gray), NOT 0.00; Δ > 6 = mismatch.
16. Join scene ↔ start_frame FROM `scenes.json` in every verification script. Hand-typed per-scene frame indices caused a false "select-vs-raw pipeline drift" investigation (scene 24 = f14194 ≠ f14250 = scene 25); the corrected check + a same-index select-vs-raw scan (all Δ ≈ 1.2) proved the index spaces agree everywhere.
17. Whisper hallucinates stock lines on short instrumental blips (measured: "Thanks for watching!", no_speech_prob 0.81, on a 1.7 s piano outro of a November-Rain rendition). Audio-map first (1a); flag such lines uncertain in the deliverable.
18. scdet is the right quiet-cut net for AI jump cuts between near-identical framings (MAD ≤ 7, below tiers) — and it corroborates every real MAD cut (all high scores). Local ffmpeg 6.1.1: no `lavfi` filter; `scdet` + `metadata=mode=print:file=` works, key `lavfi.scd.score`, one line per frame = index-aligned.

