---
name: blender-director
description: Use when directing cinematic Blender scenes via mcp__blender__* tools — a prompt becomes a shot list (dialogue/action), colored placeholder characters, 24fps mp4 export of 2–15 s plus MANDATORY cued .md + H3 prompt sheets. Workbench flat-color minimal look by default (no sky/props/textures unless requested). All artifacts go in the per-scene asset folder `generated/movies/<YYYY-MM-DD>/<scene-name>/`. Covers MCP connect procedure, Blender 5.1.2 API quirks, framing math, per-frame camera bake, render/encode pipeline, cue-sheet format, and version-timestamp naming.
---

# Blender Director runbook (Blender 5.1.2 via MCP)

Role: **movie director**. The user gives a prompt; you analyze it, invent the beats/dialogue when asked, design coverage that makes it as cinematic as possible, then build + render + export ONE mp4 **and its cued .md sheet** (mandatory).

## Standing constraints (user rules — do not re-ask)

- Characters are **colored placeholders** (cubes of the given dimensions; a placeholder mannequin is allowed if it reads better, but rigging is complex — prefer static poses via rotation keys). **Every object in the scene has a different color.**
- **Face is visible by default** whenever people are involved, unless instructed otherwise (e.g. a cinematic cut showing hands or feet). Anatomy mapping of a placeholder cube: **head on top, hands more or less in the middle, feet at the bottom**. Place eyes near the top so orientation reads in OTS shots.
- **Minimal look by default: WORKBENCH is enough.** No sky, no textures, no props unless requested. Materials carry **color information only** (flat colors). A single flat-color ground plane (different color from characters) is fine and recommended — parallax makes camera moves readable.
- **Props when requested**: properly sized is what matters; shape need not be accurate (a cube suffices), each item a different color.
- **fps is always 24**; scene length **2–15 s**; export **mp4, and only once we finish** (no intermediate video exports).
- **After exporting the video you MUST also export a cued .md file** (format below).
- **If instructed**: save the scene as a `.blend` so it can be reopened; clean the scene and start from scratch.
- **Version-timestamp naming, always**: saved files AND props get `YYYY-MM-DD-HH-MM-friendly-name` (e.g. `2026-09-04-21-11-scene.mp4`, object names prefixed/suffixed with the same stamp).
- **Asset folder per scene (v4)**: ALL artifacts of a scene live in `generated/movies/<YYYY-MM-DD>/<scene-name>/` — date = `date +%F` at build time (till day), scene name chosen by the agent (short kebab-case, e.g. `alley-corner`). Inside: `.blend`, PNG sequence dir, `<timestamp>-<name>.mp4`, `-cues.md`, `-cues-h3.md`. Filenames keep the full `YYYY-MM-DD-HH-MM-` timestamp prefix.

## Environment (this box)

- Blender 5.1.2 binary: `/home/oem/Downloads/blender-5.1.2-linux-x64/blender` (not on PATH).
- **GUI instance is user-managed** — check `ps aux | grep -i blender` and `ss -ltn | grep 9876`; never start a second GUI Blender. MCP works when the addon is connected (N-panel → MCP for Blender → Connect, port 127.0.0.1:9876).
- **Two-plane workflow**: build interactively in the user's GUI via `mcp__blender__execute_blender_code` running `exec(open('<script>').read())` (user sees the scene appear); **render headless** with a separate `--background` process as a background bash job.
- The agent model here is **text-only**: you cannot see frames. QA = exit codes + PNG file sizes (blank ≈ few KB, real ≈ hundreds of KB) + framing computed analytically before baking.
- VRAM: LLM holds ~30 GB of the 5090's 32 GB; Workbench scenes are trivial (~<1 GB). Preflight with `system_stats_local` anyway. Never touch llama-server or local ComfyUI 8188.
- Inline preview: loopback server serves `generated/` at **http://127.0.0.1:8765/** — embed `![name](http://127.0.0.1:8765/movies/<file>.mp4)` in the final message (.mp4 renders as `<video controls>`). Restart if the job is gone (`python3 -m http.server 8765 --bind 127.0.0.1 --directory generated`).

## Blender 5.1.2 API surface — EMPIRICAL, this build differs from docs

Verified 2026-09-04 (hash ec6e62d40fa9). **Probe before trusting** (`print(dir(...))`, enum lists) and guard exotic assignments with try/except + print:

| Thing | This build says |
|---|---|
| Engine ids | `'BLENDER_EEVEE'` (NOT `BLENDER_EEVEE_NEXT`), `'BLENDER_WORKBENCH'`, `'CYCLES'`. Default scene engine is **WORKBENCH** — which is the desired default anyway; set it explicitly. |
| Flat materials (Workbench) | `mat.use_nodes = False; mat.diffuse_color = (r, g, b, 1)` — color-only, no textures. |
| Sky/world | No NISHITA sky node (types SINGLE/MULTIPLE_SCATTERING/PREETHAM/HOSEK_WILKIE, only a Vector input). **Don't build skies unless requested** — leave the world at its default or set a flat background color. |
| Denoiser | `scn.eevee` has no denoise attribute (legacy EEVEE) → if you ever use EEVEE: `taa_render_samples = 64`, look id `'AgX - Punchy'`. |
| Video export | `render.image_settings.file_format = 'FFMPEG'` REJECTED by filtered enum → **PNG sequence + system ffmpeg** (recipe below). |
| Actions | Layered: fcurves at `obj.animation_data.action.layers[0].strips[0].channelbags[0].fcurves`. Keyframe *insertion* via `obj.keyframe_insert(...)` is unaffected. |
| Screenshots | Addon viewport-screenshot stubs broken → verify with real renders (`bpy.ops.render.render(write_still=True)`). |

## Director's method

1. **Beats first.** For a dialogue prompt: write the lines, time them (≈2–3 s/line ≈ 48–72 frames each), assign speaker per shot.
2. **Shot list — one line = one shot; EACH CAMERA CHANGE IS A SHOT** (number shots by camera move, not by dialogue turn). Alternating coverage: wide establishing → OTS reverse pair → close on the emotional beat → whip pan for the sharp retort → two-shot pull-back & rise to end.
3. **Camera rig**: one camera + `TRACK_TO` constraint onto an Empty target; DOF `cam.data.dof.focus_object = target` (focus racks automatically when the target moves — e.g. tilt-up drifts focus from character to sky).
4. **Bake per-frame keys** (full control, no f-curve surgery): every frame gets `(P, T, lens, fstop)` from the shot table with `smoothstep` easing; whip pan = 8–9 frame swing between two (P,T) states then a push-in hold; ±3 mm low-frequency sine "handheld" wobble on P.
5. **Framing math (do this for EVERY shot — you can't see the frames).** Sensor: 36 mm wide, vertical = 20.25 mm at 16:9. At distance d with lens L (mm): `halfW = 18·d/L`, `halfH = 10.125·d/L`. Rules: subject top above target ≤ ~90% of halfH; eyes within ±40% of halfH; OTS shoulder 1.2–2 m from camera, subject 2–3 m. Lens grammar: 35 mm wides, 50 mm OTS mediums, 60–85 mm closes. Face visibility: frame so the head zone (top ~20% of the cube) stays in shot unless the shot is explicitly a hands/feet cut.
6. **Character performance**: speaker leans toward partner ±0.05 rad with a 5-frame envelope + z-bob while talking; idle sway when silent. A faces +X, B faces −X (positive rotY leans A's top toward B).

## Cue sheet — MANDATORY after every video export

File: `generated/movies/<YYYY-MM-DD>/<scene-name>/YYYY-MM-DD-HH-MM-<name>-cues.md` (same timestamp as the mp4, same asset folder). Contents:

1. **Header**: duration, fps, frame count, codec/resolution; links to the .mp4 and .blend filenames.
2. **Subjects table**: one row per `<Subject #>` — color (RGB), name, placeholder description (dimensions + head/hands/feet mapping). Environment items listed separately as "not subjects".
3. **Shot lines**, one per camera change:
   ```
   [Shot N] at MM:SS.mmm — camera: <move description incl. lens/fstop>. Character X says "<line>".
   ```
   Cue time = shot start, computed as `(first_frame − 1) / 24` in `MM:SS.mmm`. Shots with no dialogue still get a line (camera description only).

## H3 prompt file — MANDATORY after every video export

File: `generated/movies/<YYYY-MM-DD>/<scene-name>/YYYY-MM-DD-HH-MM-<name>-cues-h3.md` (same base name and folder as the cue sheet, suffix `-h3`). It is a **MiniMax-H3 full-reference-mode prompt** for regenerating the cut with real references, formatted per the bundled guide `skills/blender-director/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md` (source: https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md). Six sections in order: `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music`.

Rules for our pipeline:
- **Our colored sticks are the `<Subject N>`** — define each with detailed appearance taken from the actual cut (color, dimensions, face markers, head/hands/feet zones, pose/lean). The environment gets its own `<Subject N>`; the style goes in the one-or-two-sentence opening of `detailed_description`.
- **The Blender cut is `<Video 1>`** — it provides shot order, cut times, camera moves, subject placement, and dialogue timeline. That is how prompt ↔ video ↔ cues stay aligned for every future version of the scene.
- Dialogue: exact lines from the cue sheet in `<d>[English] ...</d>`, speakers `(S1)`/`(S2)` assigned by first-vocal-event order; shots as `[Shot 1]` (no timestamp) then `At MM:SS.mmm`; aim for ~350–500 words on generation tasks, prioritizing the complete spoken timeline.
- **Picture references**: when the user attaches images describing the scene, add `<Picture N>` lines and fold them into the relevant `<Subject N>` definitions (appearance then comes from the picture); switch retention markers to `attribute_transfer` where a stick placeholder is being replaced by a referenced character. Until pictures arrive, detail appearance purely from the cut — that is the expected first version.

## Render → encode pipeline (proven)

One idempotent Python script (clears scene, rebuilds, CLI phases): `blender --background --python <script> -- build|test [frames]|anim`. **First create the asset folder** `generated/movies/<YYYY-MM-DD>/<scene-name>/` (date from `date +%F` at build time) and point every output — `.blend`, `seq/`, mp4, cue sheet, h3 file — into it.

1. **build** — flat-color Workbench scene; if instructed, `save_as_mainfile` to a timestamped `.blend`; run via MCP in the GUI so the user sees it.
2. **test** — 7 frames (one per shot incl. whip midpoint) at 50% res → seconds on Workbench; check exit 0 + PNG sizes.
3. **anim** — `scn.render.filepath = seqdir/'f_'` → `f_0001.png…`; Workbench renders near-instantly (EEVEE ~0.3–1 s/frame at 1080p if ever needed). Background bash job.
4. **Encode (the only export)**:
   ```
   /usr/bin/ffmpeg -y -framerate 24 -i seq/f_%04d.png -c:v libx264 -crf 18 -preset slow \
     -pix_fmt yuv420p -movflags +faststart YYYY-MM-DD-HH-MM-<name>.mp4
   ```
5. **Cue sheet + H3 prompt file** (both mandatory, above) → **verify** `ffprobe` (duration = frames/24, h264, 1920×1080, 24 fps) → deliver the 8765 preview link + shot list + dialogue in the final message.

## Reference implementation

- `/home/oem/Apps/deepseek-workspace/blender-director/alley_corner_chase.py` — **canonical v2/v3/v4 reference**: full minimal Workbench chase scene (8 shots incl. whip pan, OTS, close-up crouch; per-frame bake; build/test/anim phases) with all artifacts in the asset folder `generated/movies/2026-09-04/alley-corner/`. Copy its structure for new scenes.
- `/home/oem/Apps/deepseek-workspace/blender-director/weather_time_dialogue.py` — complete working scene (weather/time dialogue, 6 shots incl. whip pan, tilt-up with focus rack). **Note: built under the older richer look (EEVEE + gradient sky + checker ground)** — reuse its shot-table/bake mechanics only; follow this skill's minimal Workbench defaults for new scenes.
