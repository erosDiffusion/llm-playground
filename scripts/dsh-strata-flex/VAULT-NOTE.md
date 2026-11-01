Vault copy of the workspace bundle `dsh-strata-flex` — the footer VRAM control. Source of
truth stays at /home/oem/Apps/deepseek-workspace/dsh-strata-flex (copied 2026-11-01).

What the 2026-11-01 change adds: `action: "set"` on the existing /api/strata-flex route, taking
a slider value in MiB. The engine itself accepts ANY integer >= 0 with no floor, so the route owns
the guard: clamp to set_min_mib..set_max_mib (default 2048..22016), snap to the engine's 512 MiB
resize segment, refuse reclaim while ComfyUI reports a busy queue (:8188/queue_prompt), and a
dry_run flag that answers the clamped value WITHOUT touching the engine (that is how it is tested
safely). The client shows the slider on hover over the lower-brain button and applies ONE engine
call per settle (700 ms after the last change, or on drag release / mouse out), never per pixel.
