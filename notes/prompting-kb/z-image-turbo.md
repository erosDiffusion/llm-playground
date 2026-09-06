# Z-Image Turbo — workhorse T2I (remote 10GB box)

## Canonical recipe (do not "fix" — model-specific, verified)

UNET `z_image_turbo_bf16.safetensors` · CLIP `qwen_3_4b.safetensors` type **lumina2** · VAE `ae.safetensors` · **ModelSamplingAuraFlow shift=3** · negative = ConditioningZeroOut of positive · KSampler `res_multistep`, cfg 1, denoise 1. Template: `comfyui/z-image-turbo.workflow.json`; edit nodes `57:27`(text) / `57:13`(w/h) / `57:3`(seed/steps).

## Prompt behavior (observed)

- CFG-free (cfg=1, zeroed negative) → **phrase positively**, same family rule as klein.
- Text-only consistency backbone = verbatim character/style/interior blocks per shot (storyboard playbook); loose descriptions drift (observed: altar shape changed between two shots describing it loosely; explicit shared block + klein reference-edit fixed it).
- ~10–30 s/image at 1024², ~20 s at 1920×1080 on the RTX 3080.
- `mcp__comfyui__generate_image` FAILS here (SD1.5 template, no checkpoint) — always run_workflow with this recipe.

## Storyboard mode

Full process: `comfyui/storyboard-playbook.md` (beat sheet → character sheets → style block → shot prompts → L1/L2 ladder → manifest → reroll policy). User preference: simple text workflow only; consistency from identical description text.
