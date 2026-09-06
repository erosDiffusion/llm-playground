# h3-prompts/ — MiniMax-H3 prompt toolkit (fl2va — first-last-to-audio-video format)

Provenance: copied 2026-09-06 from `$HOME/Progetti/stream-h3` (the local FastH3 streaming project). The full project — inference engine `stream_fasth3.py`, job submitter `submit_h3.py`, `FastH3_4step_T2VA.json` workflow, scene + character pools — stays local; only the prompt-creation mechanism is archived here. Scene *content* files are deliberately not in this repo (see note at bottom).

## What's here

| file | what it does |
| --- | --- |
| `build_h3_characters.py` | Builds the character name pools (`h3_characters.json`: `curated` + `full`) from the community H3 known-characters index (HF dataset `malcolmrey/various`, `h3-center/known-characters/INDEX.md`). Only the `good` (verified-usable) section is taken — `onthefence`/`bad` rows exist precisely because the model does not reproduce those names reliably. |
| `validate_scenes.py` | Checks a scene pool against the H3 prompt grammar before it goes live. **This file is the hard-won knowledge**: it encodes the documented shot/cut/motion vocabulary plus phrases *measured* to be silently ignored by the model. |

## The fl2va prompt format (first-last-to-audio-video)

This toolkit targets the **fl2va** checkpoint family (first/last frame in → audio+video out — note the `overall_soundscape` + `non_diegetic_music` sections *are* the audio spec). Don't confuse it with **ref2va** (reference-to-video), the separate checkpoint variant whose reference-mode prompts (`<Subject N>` definitions + `<Video N>`/`<Picture N>` references) are what the `blender-director` preset writes into its `-cues-h3.md` files.

Scene pools are text files; blocks separated by a `---` line. One block = one clip:

```
For the target video, at 0.00 seconds into the target video, <Picture N> (from Shot M) is fully referenced.   ← first-frame reference header (fl2va); omit for plain T2VA

integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium shot frames {NAME} (S1) ... . The camera pushes in with small amplitude at slow speed. [Shot 2] At 00:07.500, the shot cuts to a close-up ... saying (S1): <d>[English] line of dialogue.</d>
overall_soundscape: diegetic sound design (room tone, materials, bodies, weather)
non_diegetic_music: music description or N/A
```

Grammar enforced by `validate_scenes.py` (H3 base-en guide §4.2–4.7):

- the three sections present **and in order**
- `[Shot 1]` carries **no timestamp**; later shots numbered consecutively, each opening with one of the five documented cut verbs (`the camera cuts to`, `the shot cuts to`, `the shot transitions to`, `the shot changes to`, `the shot switches to`) and a strictly increasing `MM:SS.mmm` inside the clip duration (frames/fps — H3 authors motion at 24 fps)
- camera motion only from the fixed vocabulary (zoom/push/pull/pan/truck/tilt/pedestal/arc/tracking/static/shake/pov/roll); **banned phrases measured to be ignored** (A/B tested 2026-08-22): `locked-off`, `the camera does not move`, `camera remains still`, `slowly and continuously`, `handheld feel`, `steadicam`
- dialogue inside `<d>[English] ... </d>` with speaker ID `(S1)` outside the tags; every speaker that speaks is introduced in the same block
- character placeholders `{NAME}`, `{NAME2}`… contiguous from 1

## Character draw mechanism (from `stream_fasth3.py` PromptPool — logic documented here, code stays local)

Scene pools carry `{NAME}`…`{NAME9}` placeholders instead of baked-in names, so N scenes × M characters = N×M distinct clips. Per draw: a share (`--curated-share`, default 0.3) of picks come from the small `curated` pool (strongest text-only recognitions), the rest from `full`; ensemble slots are forced **distinct** (a five-hander is five different faces); substitution runs **longest-first** so a `{NAME}` replacement can never corrupt `{NAME2}`. The scene's file index is returned with each draw so a clip on screen traces back to its block — the only way to act on "that one looked wrong" without regenerating.

## Related (local, not archived)

- Full project: `$HOME/Progetti/stream-h3/` — engine, submitter, workflow JSON, scene + character pools
- The **ref2va** reference-mode prompts (`<Subject N>` definitions + `<Video N>`/`<Picture N>`) are what the `blender-director` preset writes into its `-cues-h3.md` files (guide in that skill dir: `VIDEO_PROMPT_WRITING_GUIDE_ref_en.md`, source HF `MiniMaxAI/MiniMax-H3`) — a different checkpoint family than this toolkit's fl2va format

## Execution direction (user, 2026-09-06)

H3 runs should be driven by **director-style agent skills** through the ComfyUI MCP tools (remote box for images; local 8188 for video), not by raw scripts like `stream_fasth3.py`. The scripts above are the *prompt-side* toolkit; execution orchestration belongs to an agent skill (draft pending).

## Note on content

Scene pool files and character pools live locally only. This repo keeps the **mechanism + grammar**, not the content: some local scene material is adult in nature and references real people by name — that does not belong in a public repo, and neither do the name pools it was built with.
