# DLSS 5 video upscale

- **Type:** explore / integrate
- **What:** NVIDIA DLSS 5 applied to video — upscaling generated clips (H3 output, Blender renders) with current-gen upscale/frame generation.
- **Why I want to try it:** Cheap post stage for the pipeline: H3 renders come out at fixed low res; a good upscale pass makes outputs presentable without re-rendering. We have an RTX 5090, so hardware is not the constraint.
- **Fits stage:** post-processing (after H3).
- **Open questions:** DLSS 5 video-mode requirements (driver version, API surface); quality on AI-generated vs photographic footage; integration point (ffmpeg filter? ComfyUI node? standalone pass?).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
