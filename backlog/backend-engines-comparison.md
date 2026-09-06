# Backend engine comparison (unsloth vs vllm vs ollama vs lmstudio vs llama.cpp)

- **Type:** explore / know-how
- **What:** Finish the exploration of LLM backend engines — unsloth, vllm, ollama, lmstudio, llama.cpp — across performance, resource usage, stability, and capabilities.
- **Why I want to try it:** We currently run on unsloth llama-server (Qwen3.8-27B, 128k ctx, MTP); a proper comparison tells us if another engine buys real headroom for the park/agent split or future local models.
- **Fits stage:** meta / infra.
- **Open questions:** test matrix (same model, same ctx; tok/s + VRAM + stability over long sessions); does vllm beat unsloth on our 5090?; lmstudio studio integration vs raw server; park-engine implications (thin brain on :57600).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
