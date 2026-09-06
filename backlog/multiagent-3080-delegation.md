# Multi-agent coordination on the 3080 box

- **Type:** integrate / infra
- **What:** Coordinate work across agents/machines: external image generation via ComfyUI on the 3080 box (partly implemented already); delegate to Antigravity (ABO) and Copilot (ABO) to save tokens and distribute work between local and frontier models.
- **Why I want to try it:** Cheap capacity where it's cheap — token savings + parallelism; the 3080 box is already our remote ComfyUI target (192.168.1.34:9000).
- **Fits stage:** meta / infra.
- **Open questions:** which task classes go where (image gen → 3080; code/analysis → antigravity/copilot; heavy video stays local); how delegation is triggered (preset? skill? explicit ask); result collection + verification flow.
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
