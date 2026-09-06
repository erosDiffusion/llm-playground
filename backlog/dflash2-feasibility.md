# DFlash2 feasibility for Qwen3.8-27B

- **Type:** explore / know-how
- **What:** Investigate DFlash2 feasibility — what it is, how to convert Qwen3.8-27B to it (if a conversion step is needed), and its performance vs our current presets (unsloth llama-server: Q4_K_M, 128k ctx, bf16 KV, MTP spec decode).
- **Why I want to try it:** If DFlash2 buys real speed or headroom on the 5090, it could replace/augment the current preset stack for the agent LLM and/or the park engine; complements [backend-engines-comparison](backend-engines-comparison.md).
- **Fits stage:** meta / infra (agent LLM + park engine).
- **Open questions:** pin down exactly what DFlash2 refers to in our context (speculative decoding? new quant format? separate engine?) — find the papers/impls first; conversion path for Qwen3.8-27B (GGUF → ?); expected tok/s vs current presets at same ctx; VRAM delta on the 5090 with ~1.5–2GB free while I run; park-engine (:57600) implications.
- **Related:** [backend-engines-comparison](backend-engines-comparison.md), [vsa-pdd-acceleration](vsa-pdd-acceleration.md).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
