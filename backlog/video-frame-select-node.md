# Video frame select/export node (ComfyUI)

- **Type:** build
- **What:** A custom ComfyUI node to efficiently select and export any video frame.
- **Why I want to try it:** First-frame extraction is a constant micro-step in the pipeline (H3 needs the look-anchor frame from previs renders); doing it fast/lossless in-graph removes file shuffling.
- **Fits stage:** previs→H3 (tooling).
- **Open questions:** selection API (timecode? index? nearest-to-description?); export quality/bitdepth; batch mode for cue-sheet frames (one per shot).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
