# Test the custom-node flows

- **Type:** test
- **What:** Validate our ComfyUI custom-node stack end-to-end: controlnet maps, frame select/export, refbox crop — real runs, not just "node loads".
- **Why I want to try it:** Nodes that load are not nodes that work; a pass/fail flow test catches breakage before the pipeline depends on them.
- **Fits stage:** tooling QA across stages.
- **Related:** [pose-camera-library-node](pose-camera-library-node.md), [video-frame-select-node](video-frame-select-node.md), [refbox-crop-node](refbox-crop-node.md).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
