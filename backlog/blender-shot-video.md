# blender-shot-video — Yi-111-a

- **Link:** https://github.com/Yi-111-a/blender-shot-video (author profile: https://github.com/Yi-111-a)
- **What it is:** Claude Code skill that turns a one-line idea into a cinematic shot: Blender gray **white-model previs** locks camera + composition, then any AI video model "paints" the final from first-frame image + previs + prompt. Core insight: feed a *plain gray blockout* (the model reads volume/depth, not a flat picture) instead of a textured scene — avoids flat-image artifacts; iterate the blockout for free, pay only when the move is right. Demonstrated against Seedance 2.0.
- **Why I want to try it:** This is almost exactly the north-star flow — it documents the exact recipe (first frame + white-model previs + director-shot prompt) for driving an AI video model with Blender output, and shows working examples of the same camera in both renders.
- **Fits stage:** Previs render → H3 input. Our H3 template (`h3.test.1ref.json`) currently takes a single reference image; the question to answer: does H3 accept a previs *video* as motion reference, or only first-frame + prompt? If video-ref works, this repo's pipeline maps 1:1 onto our local stack (Blender 5.1.2 + `blender-director` preset for scene building).
- **Same author, related:** `MiniMax-H3-Turbo` (tracked separately), `VideoAir-MiniMax-H3-LowVRAM` (8GB-GPU H3 weight streaming — low priority: we have a 5090/32GB), `ai-character-video-pipeline` (2D→3D character→rig→video→repaint; watch).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try) from user link.
