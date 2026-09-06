# MiniMax-H3-Turbo — Yi-111-a

- **Link:** https://github.com/Yi-111-a/MiniMax-H3-Turbo
- **What it is:** Standalone acceleration layer for MiniMax H3 — plugs into the official `MiniMaxAI/MiniMax-H3` Diffusers modular pipeline directly, no ComfyUI. Targets consumer GPUs (RTX 3090/4090 class); claims faster + lower-VRAM local video generation.
- **Why I want to try it:** H3 render speed is the bottleneck of the north-star loop (each shot costs a full H3 pass). If this layer speeds things up without rehosting the model, it's a drop-in win; at minimum it's a reference for what's possible with the same weights.
- **Fits stage:** H3 speed / VRAM headroom.
- **Open questions:** Does it support the variants we run locally (fl2va bf16 / ref2va int8_convrot + turbo/ref LoRAs)? It's Diffusers-native, so it would be a *parallel* path to our ComfyUI graph, not a replacement — compare outputs before switching anything.
- **Related:** `VideoAir-MiniMax-H3-LowVRAM` (same author) — weight streaming for 8GB GPUs; lower priority since we have 32GB VRAM, but useful knowledge if parking pressure ever grows.
- **Status log:**
  - 2026-09-06 — added to backlog (watch) from user link.
