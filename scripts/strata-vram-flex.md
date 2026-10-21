# Strata VRAM flex API (local box) — the on-the-fly GPU window

Provenance: probed live on the 5090 box, 2026-10-21 (engine v0.2.2 / serve layer in `~/Apps/Strata`).
Standing protocol owner: `~/.dsh/AGENTS.md` "Strata flex protocol"; decision log 2026-10-19 (flex nodes, busy-target) and 2026-10-21 (never park/resume again).

## What the engine is

- Agent brain = **qwen3.8-flash-next**, IQ3_S MoE pack (10,816 experts), served by the
  **Strata** engine: `strata --serve --pack iq3_s --vram-elastic` + `serve/server.py` on **:8080**
  (+ `strata-vision` sidecar ≈1.7 GB). Config `~/Apps/Strata/strata-iq3_s.json`: `"vram_elastic": true`,
  start flag `--vram-reserve-mib 2048`. DSH route: profile `web-lite` row `agent-default-model`
  → provider `strata`, model `qwen3.8-flash-next-iq3_s`.
- Because of `--vram-elastic` the **expert cache lives in 512-MiB segments** and can be
  grown/shrunk live: no model swap, no session loss — this replaces the old park/resume ceremony entirely.

## The API

Read/flex/reclaim are the same call (`reserve_mib: null` = back to the start reserve, 2048):

```bash
# flex down — keep N MiB free for other programs:
curl -sX POST 127.0.0.1:8080/v1/vram -H 'Content-Type: application/json' -d '{"reserve_mib": 22016}'
# reclaim to start state:
curl -sX POST 127.0.0.1:8080/v1/vram -H 'Content-Type: application/json' -d '{"reserve_mib": null}'
```

- Applied **between requests**: the serve layer holds the FIFO, waits up to 300 s for an
  in-flight request; `ModelBusy` = a request is still running → retry at the next tool boundary.
  The engine itself never resizes mid-request. An unloaded engine applies it at load.
- Response (the state probe — always verify after flexing):
  `{"status":"ok","reserve_mib":N,"expert_slots":…,"expert_slots_full":10816,`
  `"expert_cache_mib":…,"expert_cache_full_mib":21019,"vram_free_mib":…,"prompt_chunk":8192}`

## Numbers (measured 2026-10-21, re-probe before trusting)

- Slot ≈ 1.94 MiB. Full cache = 10,816 slots ≈ 21.0 GB. Full state: engine ≈ 30.5 GB, ~1.5 GB free.
- `reserve_mib: 22016` → **~512 experts resident** (cache ≈1 GB) → engine ≈ 9–12 GB,
  ~20 GB free → window fits MiniMax-H3 (~22–27 GB headroom incl. Comfy's share), klein (~10–15 GB),
  DLSS5-NR-Wine host (~1–2 GB; small tests even fit unflexed).
- Busy-target while a Comfy flow runs: `reserve_mib: 14336`-style flex → engine ≈18 GB, ≥2 GB headroom
  (user-tuned 2026-10-19; do NOT full-reclaim mid-flow).

## Protocol (user standing policy)

1. Flex to floor as the **last** action right before starting/handing off a ComfyUI flow.
2. Reclaim (`null`) immediately after the flow ends — think at full speed by default.
3. Never process-kill the engine/vision sidecar; VRAM moves **only** via this API.
4. In-graph alternative: `StrataFlexDown` / `StrataReclaim` pass-through nodes
   (`custom_nodes/comfyui-strata-flex`) embed the same calls inside a workflow (flow 17 pattern).
5. `agent-park.sh` / `agent-resume.sh` / park-thin = superseded studio-era scripts — do not call.
6. While flexed low, agent inference is slower (experts stream from RAM) — acceptable; it worked
   through full H3 renders (2026-10-20, ~12 GB state).
