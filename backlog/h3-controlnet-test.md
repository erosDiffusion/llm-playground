# ControlNet test for H3

- **Type:** test
- **What:** Test ControlNet conditioning on MiniMax H3 (local ComfyUI already carries fun controlnet union + H3 motion-context custom nodes).
- **Why I want to try it:** If H3 accepts control maps, camera/pose guidance becomes a first-class input — much stronger than prompt-only motion control; feeds [pose-camera-library-node](pose-camera-library-node.md) directly.
- **Fits stage:** previs→H3 (motion control).
- **Open questions:** which control modes work with our H3 variants (fl2va bf16 / ref2va int8_convrot); strength tuning vs artifacts; does it replace or complement the white-model previs approach?
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
