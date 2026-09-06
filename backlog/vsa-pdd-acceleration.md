# VSA / PDD acceleration know-how

- **Type:** explore / know-how
- **What:** Study + apply VSA and PDD techniques for accelerating video-model inference.
- **Why I want to try it:** H3 render speed is the loop bottleneck; every % of speedup compounds across shots. Complements [minimax-h3-turbo](minimax-h3-turbo.md) (product-level acceleration).
- **Fits stage:** H3 speed / VRAM headroom.
- **Open questions:** pin down exactly what VSA/PDD refer to in our context (sparse attention? dynamic decoding?) — find the papers/impls first; compatibility with our int8_convrot weights + LoRAs.
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
