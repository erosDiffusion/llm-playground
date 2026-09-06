# Preset video-driven movie actions (Blender v2v flow)

- **Type:** build / experiment — the north-star core loop
- **What:** Create dummy movies in Blender: sequences of preset actions + preset camera moves, integrate them into the Blender→video (v2v) flow, test drive. Concrete instantiation of the previs→H3 stage.
- **Why I want to try it:** This is the experiment that proves the north star: canned action/camera library in Blender → render previs → feed H3 → compare. If preset moves work well they become reusable "shots" for any description.
- **Fits stage:** previs→H3 (see [blender-shot-video](blender-shot-video.md) for the external recipe this mirrors).
- **Open questions:** which preset actions/camera moves to standardize first; how H3 consumes the rendered previs (video ref vs first-frame only); keeping Blender cuts aligned with H3 shot order (we already do cue sheets + `-cues-h3.md` in `blender-director`).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
