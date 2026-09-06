# MiniMax H3 — video prompting (fl2va & ref2va)

Distilled 2026-09-06 from the BFL-style VIDEO_PROMPT_WRITING_GUIDE_ref_en.md (blender-director skill dir), `llm-playground/projects/h3-prompt-toolkit/` (validate_scenes.py grammar + character pools), and live production use (Mongo banana scene, 2026-09-06 — gemma-written prompt passed the format rules).

## Two checkpoint variants (don't confuse)

| Variant | In → Out | Prompt mode |
|---|---|---|
| **fl2va** | first/last frame images in → audio+video out | `integrated_multimodal_description` + `overall_soundscape` + `non_diegetic_music`; first-frame reference header: "For the target video, at 0.00 seconds into the target video, <Picture N> (from Shot M) is fully referenced." |
| **ref2va** | reference images/video/audio in → video out | six-section full-reference format below (`<Subject N>`/`<Picture N>` definitions + shot references) — what blender-director writes into `-cues-h3.md` |

## ref2va format (six sections, IN ORDER)

1. **subject_definitions** — labels:
   - `<Subject N>` = character/visible content; speaker ID `(S1)` reused wherever that speaker talks
   - `<Picture N>` = a reference IMAGE used as first frame / keyframe / last frame / composition anchor ("`<Picture 2>` is the first frame of [Shot 1], showing …"); if an image only defines character/style, cite it INSIDE the subject definition instead
   - `<Video N>` = whole-video relationships (editing source, continuation, camera-movement reference) — never replaces a subject label
   - `<Audio N>` = audio asset / synchronized track; reuse speaker global ID: "`<Audio 1>` is the voice-timbre reference for `<Subject 1>` (S1)"
2. **summary** — one short paragraph beginning with a task-type prefix, combinable with ` + `: `[keyframe completion]` (image as concrete frame anchor) · `[reference generation]` (guidance only) · `[video editing]` · `[video continuation]` · `[audio reuse]` · `[audio reference]`. Use previously defined labels; no new ones.
3. **retention_analysis** — one line per label, fixed markers: `fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`. Entry formats: `<Subject 1> (appears in [Shot 1], [Shot 3]): fully_preserved - …` · `<Picture 2> ([Shot 1] first frame): fully_preserved - …`
4. **detailed_description** — shot grammar (HARD, enforced by validate_scenes.py):
   - `[Shot 1]` carries NO timestamp; later shots open with ONE of the five documented cut verbs: `the camera cuts to` / `the shot cuts to` / `the shot transitions to` / `the shot changes to` / `the shot switches to` + strictly increasing `MM:SS.mmm` inside clip duration
   - **motion authored at 24 fps** (frames/fps)
   - camera motion ONLY from the fixed vocabulary: zoom · push · pull · pan · truck · tilt · pedestal · arc · tracking · static · shake · pov · roll
   - **BANNED phrases (A/B tested — silently ignored by the model):** `locked-off` · `the camera does not move` · `camera remains still` · `slowly and continuously` · `handheld feel` · `steadicam` → use "static" instead
   - dialogue: `<d>[English] line of dialogue.</d>` with speaker `(S1)` OUTSIDE the tags; every speaker introduced in the same block
5. **overall_soundscape** — diegetic sound design (room tone, materials, bodies, weather)
6. **non_diegetic_music** — music description or `N/A`

## Character consistency (h3-prompt-toolkit mechanism)

Scene pools carry `{NAME}`…`{NAME9}` placeholders → N scenes × M characters = N×M distinct clips. Per draw: 30% curated pool (strongest text-only recognitions), rest full pool; ensemble slots forced DISTINCT; substitution longest-first (`{NAME2}` before `{NAME}`). Only take the `good` (verified-usable) section of the known-characters index — onthefence/bad rows exist because the model doesn't reproduce those names reliably.

## Production notes (local box)

- Template: `comfyui/local/h3.test.1ref.json` (i2v, audio out). VRAM ~22–27GB → **park first** (`agent-park.sh`).
- Cued .md after every export: `[Shot N] at MM:SS.mmm`, each camera change = a shot; every export also gets `<name>-cues-h3.md` (blender-director rule).
- Small-model authoring works: gemma-E4B wrote a valid ref2va prompt in 3.4s (Mongo scene) when briefed with the rules above — brief = format + label semantics + shot grammar + one example line per section.
