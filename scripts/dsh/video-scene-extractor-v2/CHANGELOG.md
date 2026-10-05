# dsh-video-scene-extractor v2 — changelog

Source: bundle `dsh-video-scene-extractor` (github erosDiffusion/dsh @ 7dc012c1), copied 2026-10-05 after a live run on `prn_00389_.mp4` where every step 0–8 hit at least one runbook/script mismatch. The installed skill dir is read-only (PATH CONTRACT) — this folder is the fix candidate for upstream.

## Fixed (all reproduced + re-verified end-to-end 2026-10-05)

| # | File | v1 problem (hit live) | v2 fix |
|---|---|---|---|
| 1 | mad_scan.py | runbook passes `--quiet`; argparse aborts: "ambiguous option: --quiet could match --quiet1, --quiet2" | real `--quiet` store_true flag |
| 2 | mad_scan.py | writes pkt_pts/mad/cand_manifest at out_dir ROOT, but runbook edge-case check + step-8 layout say `data/` | writes everything under `<out_dir>/data/` |
| 3 | consolidate.py | reads `<out_dir>/pkt_pts.csv` only → FileNotFoundError once intermediates live in data/ (v1 run needed a root symlink) | `locate()`: data/ first, root fallback |
| 4 | consolidate.py | transcript segments + no `--speakers` → `ValueError: min() iterable argument is empty` crash | guard: empty map → speaker `unknown`, confidence `uncertain` |
| 5 | consolidate.py | never writes `onsets.txt`, but runbook step 6 consumes `data/onsets.txt` (v1 run: hand-derived) | writes `data/onsets.txt` (JSON array) after scenes.json |
| 6 | consolidate.py | pkt_pts lines with trailing comma (`-0.032000,`) crash `float()` | strip + rstrip(',') |
| 7 | extract_frames.py | onsets file containing a bare number parses via json.loads to int → `TypeError: 'int' object is not iterable` (escapes the JSONDecodeError fallback) | isinstance check; bare number / JSON array / one-per-line all work |
| 8 | montage.py | crashes `FileNotFoundError: montages/_a.png` when out dir missing | auto-makedirs of the out_prefix dir |
| 9 | hashcheck.py | runbook step-8 call `hashcheck.py <video> frames/ scenes.json` does not exist (script only takes 2 PNGs) — the whole step-6 raw-pipe verification had to be hand-written | `verify` mode implements the documented protocol: raw gray pipe 320×180 passthrough, start_frame joined from scenes.json, Δ≤6 MATCH (baseline 1.0–1.8), exit 1 on mismatch; 2-PNG arbitration mode kept |
| 10 | check_ffmpeg.py | greps `ffmpeg -h formats` for `-lavfi` → "✗ lavfi filter flag: NOT SUPPORTED" on ffmpeg 6.1.1, the version the skill REQUIRES; tells users to upgrade a working install | tests the filters actually used: scdet, select, metadata, scale |
| 11 | SKILL.md | scdet metadata documented as 2-line `:`-separated pairs; real output is 3 lines/frame (`frame:` + `lavfi.scd.mafd=` + `lavfi.scd.score=`, `=` separators) — first parse attempt failed | corrected format note |
| 12 | SKILL.md | step-7 invocation `montage.py <video> <frames_dir> montages/` ≠ real signature `<frames_dir> <scenes.json> <out_prefix>` | invocation corrected |

## End-to-end proof (2026-10-05)

`~/Apps/generated/prn_00389_-v2test/` — the SKILL.md invocation block run VERBATIM (no --speakers, static-video path) on prn_00389_.mp4: check_ffmpeg all-green → mad_scan --quiet OK → edge-case legacy created → consolidate (no crash, speaker fallback unknown/uncertain) → extract_frames from auto-written data/onsets.txt → montage (dir auto-created) → hashcheck verify: `mean|delta|=1.34 -> MATCH`, exit 0. Zero manual intervention, zero deviations.

## Unchanged
Detection logic (MAD tiers, clustering, scdet net), sheet_builder, schemas, and all Hard-won catalog rules are untouched — v2 only removes invocation friction.

## How v2 is loaded in this deployment (2026-10-05, web-lite profile)

`~/.dsh/profiles/web-lite/cordis.patch.yml` gained three entries (verified via `pnpm dsh --profile web-lite --dump-config`):

1. `- id: video-scene-extractor` + `disabled: true` — kills the bundle's host row (it registers shellEnv `DSH_VIDEO_SKILL_DIR` + `/video-extractor`, with SKILL_DIR hardcoded from the package location — a config override cannot redirect it).
2. `- insert:` row `video-scene-extractor-v2` → `plugin/index.js` (this folder) — local twin of the bundle's host entry: same shellEnv var + same slash command, both pointing at `skills/video-scene-extractor/` in this folder.
3. `- id: preset-video-scene-extractor` — FULL config override of the bundle's agent-preset row.

**Cordis gotcha found (cost one broken preset):** a per-id profile-patch entry REPLACES the whole `config` object of the target row — a partial `{plugins: [skill-filesystem]}` override silently wiped the preset's identity, persona, and every tool. The bundle's comment ("override this row's config.plugins by id") is misleading. The patch therefore carries the bundle's full preset config verbatim with ONE change (`customSkillDirs` → this folder's `skills/`). Regeneration recipe after a bundle update:

```bash
python3 - <<'EOF'
import re
B = "<new-bundle>/presets/video-scene-extractor.patch.yml"   # path of the updated bundle
text = open(B).read()
m = re.search(r"^    - id: preset-video-scene-extractor\b", text, re.M)
entry = text[m.start():]
entry = "\n".join(ln[4:] if ln.startswith("    ") else ln for ln in entry.splitlines())
entry = re.sub(r"(customSkillDirs:\n(\s+)- )!!js[^\n]*\n",
    r"\g<1>/home/oem/Apps/deepseek-workspace/dsh-video-scene-extractor-v2/skills\n", entry)
open("/tmp/preset_override.yml","w").write(entry.rstrip()+"\n")
EOF
# then replace the block under the "# The bundle's preset row ..." comment in
# ~/.dsh/profiles/web-lite/cordis.patch.yml with /tmp/preset_override.yml
```

## Publish path
Drop `skills/video-scene-extractor/` (SKILL.md + scripts/) over the skill dir in the erosDiffusion/dsh repo and re-tar the bundle; once published upstream, the three profile-patch entries above can be removed (the bundle then ships v2 itself). Nothing machine-specific is in the skill itself.
