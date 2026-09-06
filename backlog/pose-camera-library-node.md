# Pose & camera-move library node (ComfyUI)

- **Type:** build
- **What:** A ComfyUI node carrying a library of poses, camera moves, etc. Base candidate: user repo https://github.com/erosDiffusion/ComfyUI-ErosDiffusion-ControlnetMaps — extend it with videos and stuff.
- **Why I want to try it:** One place to store/reuse the preset actions + camera moves from [preset-action-movies-v2v](preset-action-movies-v2v.md) inside ComfyUI graphs; pairs with SAM 3D pose derivation ([sam3d-body-poses](sam3d-body-poses.md)).
- **Fits stage:** previs→H3 (tooling).
- **Open questions:** repo is user-owned and NOT in my gh-git allowlist — work locally or add it to scope; what library entries look like (pose keyframes? camera path params? video clips?); how it feeds H3 conditioning ([h3-controlnet-test](h3-controlnet-test.md)).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
