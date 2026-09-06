# klein-matrix — FLUX.2 [klein] generate/edit test harness

Portable runner + tested prompt definitions for the unsloth studio images API (`/api/inference/images/generate`). Distilled from two live matrix rounds on an RTX 3080 box (2026-09-06): round 1 = 10 style/camera pairs (T2I + single-ref edit), round 2 = camera-angle change, character replacement, clothing replacement, multi-ref dress-up, multi-ref environment placement, typography, character sheet.

## Files

| file | what |
|---|---|
| `run_matrix.py` | runner — env-var config (`REMOTE_UNSLOTH_URL`, `REMOTE_UNSLOTH_KEY`), no secrets in code |
| `tests-v2.json` | round-2 test definitions (prompts + params; `<path-to-…>` placeholders point at your own input images) |
| `results-round1.md` | round-1 verdicts + full prompts (what works / what resists change) |
| `enrico_image_flux2_klein_image_edit_9b_distilled.json` | ComfyUI-side multi-ref klein edit workflow (UI format, 2× LoadImage into a subgraph; model links in its notes: flux-2-klein-9b-fp8 + qwen_3_8b_fp8mixed + flux2-vae) — from the local studio `user/default/workflows/` |

## Usage

```bash
export REMOTE_UNSLOTH_URL=http://192.168.1.34:8888
export REMOTE_UNSLOTH_KEY=<studio-key>
python3 run_matrix.py tests-v2.json --out ./results            # all tests
python3 run_matrix.py tests-v2.json --only t6_clothing_dressup  # one test
```

## API semantics (verified)

- `init_image` = base image to edit (img2img, `strength` applies; 0.6–0.8 for keep-layout).
- `reference_images` = list of EXTRA references bound to the prompt by content/position ("image 1" = init, "image 2" = first extra ref); klein cap ≤4 total.
- Dress-up pattern: init=character plate, refs=[clothing plate], "Dress the person in image 1 wearing the outfit from image 2…".
- Placement pattern: init=environment, refs=[character sheet/plate], "Place the character from image 2 in the exact scene of image 1…".
- No negative prompts (guidance-distilled); dims multiples of 16; ~960×544 max on 10GB VRAM; sequential calls only.

## Proven patterns & failure modes (round 1, full report in results-round1.md)

Works at strength 0.7: lighting-only edits, add-element, object replacement, background swap, era/style reskin — layout preserved every time.
Failure mode: strongly-baked reference cues resist change (wet pavement survived "dry pavement") → phrase as explicit REPLACEMENT or reroll. Minor drift on outfit/shape edits is normal.
