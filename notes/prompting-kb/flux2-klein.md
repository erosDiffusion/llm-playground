# FLUX.2 [klein] edit/reference-fusion — syntax & mechanics

## CHEAT SHEET (accessible version — read this first)

Why klein prompts behave differently (deAPI guide, 2026-04): klein is built on a **Qwen3 text encoder** (not T5+CLIP) — it reads prompts **like an LLM**: multi-sentence descriptions up to 512 tokens, spatial relationships, even logical conditions ("a cat holding a sign where the text matches the color of the cat's eyes"). Consequences:

| Do | Don't |
|---|---|
| Write **prose**, 40–120 words — that's the sweet spot | Keyword soup ("woman, 30s, Tokyo, rain") or one-word prompts |
| **Front-load the subject** — first sentence gets the most attention | Bury the subject after three sentences of scenery |
| **Name materials** ("brushed aluminum with subtle radial grain", "indigo-dyed linen") | Generic words ("metal", "cloth") |
| Describe light like a photographer: **source + quality + direction + color temperature** — highest-impact lever | Omit lighting (flat images) |
| Layer scenes **foreground / midground / background**, each with its own materials+lighting | One run-on description of the whole room |
| Phrase everything **positively** ("crisp focus, razor-sharp details") | Negative prompts — klein has no CFG and ignores them |
| Keep steps at **4** (step-distilled; our local template already does) | Bump to 20/50 "for quality" — it breaks output |
| In-image text: quote it + font style + color + placement + case | Vague "some text on the mug" |

**Editing (single/multi-ref):** one sentence per action; say what stays ("…while keeping the rest unchanged", "Change nothing else"); reference refs by position (**image 1 / image 2**, official mechanism) + distinctive attributes; when compositing, add "matching scale, lighting, and perspective"; "preserving its exact proportions, markings, finish" for identity-critical objects. Max references: BFL says **4** (klein), some providers cap at 3 — more than that → identity mixing.

**Resolution:** ≥768px per side or quality drops; sweet spot 1024–1536 (on our 10GB remote box, edits cap ≈960×544 — see limits below).

**Incompatible:** FLUX.1 LoRAs (different architecture) — multi-reference replaces most LoRA use cases. Named-artist style references DO work ("Moebius line work with Ghibli watercolor washes" merges coherently).

## Cross-check: 4 guides reconciled (fluxklein.net + deAPI + fal + Kuhr, all verified FLUX.2/klein)

**Consensus (all four agree):** prose over keywords · front-load the subject · lighting is the #1 lever (source+quality+direction+temperature[+interaction]) · name materials · editing = one imperative per action with explicit preservation ("while maintaining…", "Change nothing else") · quote in-image text + style/placement.

**New from fluxklein.net:**
- **Style/mood tag pattern** at the end of a prompt: `[scene]. Style: Country chic meets luxury lifestyle editorial. Mood: Serene, romantic, grounded.` — and camera tags: `Shot on 35mm film (Kodak Portra 400) with shallow depth of field—subject razor-sharp, background softly blurred.`
- **No prompt upsampling on klein** — "what you write is what you get; be descriptive."
- Editing principle (best phrasing found): *"Reference images carry visual details. Your prompt describes what should change or how elements combine — not what they look like."*

**New from Kuhr (andreaskuhr.com, updated 2026-08-25, whole FLUX.2 family):**
- **Precision rule of thumb:** "Imagine you are dealing with a completely clueless simpleton" — ~~"Change the color of the dress"~~ → "Change the color of the green dress of the woman in the centre to white."
- **Color gradients work:** "Change the color of the t-shirt to gradient starting with hex #006400 at the bottom and finishing with hex #ffd39b at the top."
- **Style-flip pitfall:** mixing different styles/concepts in one multi-ref image can cause style BLEND (one element's style leaks onto everything) → state explicitly which style is global and which applies only to one element.
- **Structured JSON prompts** (FLUX.2 [dev]/Mistral-encoder family): `{"scene":…, "subjects":[{description, position, color}], "color_palette":[…], "lighting":…, "mood":…, "composition":…, "camera":{angle, lens-mm, f-number, ISO}}` — per-subject positioning + camera params as data. Test on klein later (Qwen encoder may accept it).
- **Known issue — T2I faces:** Flux.2's fresh person generation is weaker than FLUX.1's; prompt-sharpening doesn't fix it → for face-critical shots, prefer editing a good reference over generating one from scratch.
- Per-variant facts: klein = "quick preliminary designs or storyboards" (exactly our use), 13GB+ cards, seconds per image; dev needs 24–32GB.

**Conflicts resolved:**
| Topic | Sources say | Resolution |
|---|---|---|
| Prompt length | fal "<100 words" · deAPI "40–120" · fluxklein "30–80 production, 80–300+ complex" | **30–120 for most work; up to ~300 only when every detail serves the image** (no filler) |
| CFG / saturation fix | deAPI: klein has no CFG · Kuhr: lower CFG 4→2 fixes oversaturation | Per-variant: **klein = guidance-distilled, no effective CFG → phrase positively + longer precise prompts**; dev/flex have working CFG (4→2) and sampler choice (Heun vs Euler) |
| Max references | BFL: klein ≤4 · deAPI: 3 · Kuhr: "up to 10" | The 10 is FLUX.2 **[dev]**; **klein = ≤4 (stay ≤3 for safety)** |
| Text encoder | BFL: Qwen3-8B · Kuhr: Mistral-Small for dev/flex | Both LLM-class → both read prose/logic; klein ships the Qwen one |

---

## Full reference (research notes + sources)

Researched 2026-09-06 from BFL official sources (model card, blog, flux2 repo CLI + KV-cache doc), the deAPI prompting guide (what-works/what-doesnt, 2026-04-29), fal's klein guide, and the proven local template `comfyui/local/klein.image.edit.json`. Sources:
- https://huggingface.co/unsloth/FLUX.2-klein-9B (BFL model card mirror)
- https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence
- https://github.com/black-forest-labs/flux2 (README, `scripts/cli.py`, `docs/flux2_klein_kv_cache.md`)
- BFL docs site: docs.bfl.ai → "Image Editing with FLUX" → Single/Multi-Reference guides (fetched raw via the `.md` suffix trick)
- deAPI blog, "Prompting FLUX.2 Klein: What Works, What Doesn't, and Why" (2026-04-29; fetched via r.jina.ai reader — page is JS-rendered): Qwen3-encoder behavior, 4-step fixed, no-negatives, 40–120 word sweet spot, front-load subject, materials/lighting/depth-layering, ≥768px floor, FLUX.1 LoRA incompatibility

## What klein is

9B rectified-flow transformer, **unified T2I + single-ref editing + multi-reference generation** in one model. Step-distilled to **4 inference steps**, guidance-distilled (guidance ≈1), 8B Qwen3 text embedder. All variants (4B/9B/Base/KV) support all three modes. "For image editing, 9B KV is faster at equal quality" (KV cache: reference tokens processed once, then cached — speedup grows with #refs and smaller output).

## Core mechanic (from BFL's own CLI — this defines the prompt contract)

1. Reference images are VAE-encoded to **image tokens and concatenated into the attention sequence** (`encode_image_refs` → `img_cond_seq`). They carry **no labels, no indices, no "image 1/image 2" tags in the prompt**.
2. The model binds references to the prompt **by content similarity** — whatever the prompt describes, it matches against the reference tokens.
3. The prompt is ONE free-text string: either an **imperative edit instruction** ("Turn this cat into a dog", "obtain the side view" ← our local template's own example) or a **declarative target description** ("a cat wearing sunglasses" + refs).
4. `match_image_size=N` — output dimensions taken from reference N (keep aspect with your background ref!).
5. Optional prompt upsampling: klein expands short instructions via the flux.2-dev text encoder, optionally SEEING the references (`upsample_prompt([prompt], img=[refs])`) — so a terse instruction is fine; a precise one is better.

## The syntax rules (what to write) — distilled from BFL official guides + fal klein guide

Model applicability verified: ALL of these are **FLUX.2 / FLUX.2 [klein]** docs (checked 2026-09-06; the docs site also has a separate FLUX 3 section — overview+video only, nothing image-editing; fal guide is explicitly `fal-ai/flux-2/klein`). Sources: docs.bfl.ai `/guides/prompting_editing_single_reference` + `/prompting_editing_multi_reference` (fetched via the `.md` suffix trick — the HTML pages are JS-rendered), fal.ai/learn/devs/flux-2-klein-prompt-guide, BFL flux2 repo.

**R1 — Be explicit about PRESERVE / EDIT / ADD.** BFL's own rule: "Be specific about what changes and explicit about what should stay the same." Their canonical phrasings: "…while keeping the rest of the image unchanged", "Change nothing else", "Keep her pose". Vague prompts are their official "Avoid" list: ~~"Make it better" / "Improve the lighting" / "Fix the image"~~.

**R2 — Positional references ARE the official mechanism.** BFL's multi-ref guide: "describe the role of each image so the model knows what to pull from where", with prompts like *"A photograph of the woman in **image 2** sitting on the swing in **image 1** and the cat from **image 3** sitting on her lap, all in the style of **image 4**"* (their UI even color-highlights `image N` tokens). fal's klein guide uses ordinals too: "The subject from the first image wearing the jacket from the second image, photographed in the environment from the third image." So: use `image N` (N = position in the reference list) **plus** distinctive attributes for clarity ("the granite altar slab in image 1").

**R3 — One sentence per action, imperative or declarative** (BFL's real examples are short):
- Preserve: "Keep the exact same <element+attributes> unchanged." / "Change nothing else."
- Edit/Replace: "Replace the DJ with a polar bear without headphones." / "Change her dress from blue to deep burgundy."
- Add: "Add small goblins climbing the right wall of the gorge."
- Transfer: "Apply the colors and patterns of image 2 to the subject in image 1. Keep the pose, lighting, and composition of image 1 unchanged."

**R4 — Compositing phrases that matter** (from BFL examples): "matching scale, lighting, and perspective" when placing a ref element into another ref's scene; "Apply the style of image N to the entire new scene" for global style binding.

**R5 — Extra capabilities:** hex color codes work ("Change the cow's white fur to #8bc4bb"); text rendering: quote exact text + font/color/placement/capitalization; natural-language emphasis instead of weights ("prominently featuring", "with particular attention to"). **Negative prompts: klein is guidance-distilled (no CFG) — deAPI reports they are ignored entirely; phrase positively** ("clean surface, unmarked" not ~~"no text, no watermark"~~). (fal's endpoint exposes a `negative_prompt` param — treat it as unreliable for klein.)

**R6 — Multi-ref limits:** **FLUX.2 [klein] supports up to 4 references**; BFL pro API caps total input+output at 9MP (1MP output → up to 8 refs on other models).

**R7 — Denoise strength (img2img mode, unsloth API `strength`):** low = close to source (preserve layout), high = more freedom. For "keep interior, swap subject" start ~0.6–0.8; style/lighting tweaks ~0.3–0.5.

**R8 — Resolution:** match the background reference (`match_image_size` / width+height = ref size) so composition transfers 1:1. (On the 10GB remote box, edits cap at ≈960×544 — see limits section.)

**R9 — Prompt structure for T2I (fal klein guide):** hierarchy subject → environment → style → technical; content words (nouns) outweigh modifiers; keep under ~100 words; always specify lighting + composition; never mix conflicting aesthetics ("photorealistic" + "watercolor"); iterate ONE element at a time with the seed fixed to isolate prompt effects.

## Where we can run it

| Path | Model | Notes |
|---|---|---|
| **Remote unsloth images subsystem** (192.168.1.34:8888, klein-9B Q4_K_M on disk) | `POST /api/inference/images/generate` with `prompt`, `init_image` (base64/img2img), `reference_images` (multi-ref list), `mask_image`+`strength` (inpaint), `controlnet`, `loras`, `width/height/steps/guidance/seed` | loads via `remote-gpu load-image unsloth/FLUX.2-klein-9B-GGUF flux-2-klein-9b-Q4_K_M.gguf`; **no parking, no downloads** — the path to use for storyboard fusion |
| Local ComfyUI (localhost:8188) | `comfyui/local/klein.image.edit.json` — UNET `flux-2-klein-9b-kv-fp8.safetensors` (the KV variant), CLIP `qwen_3_8b_fp8mixed.safetensors` type **flux2**, VAE `flux2-vae.safetensors`, **two `ReferenceLatent` nodes** (multi-ref wiring), `FluxKVCache`, 4-step Flux2Scheduler, cfg 1 | proven 3×; needs parking first (~10–15GB) |
| Remote ComfyUI (:8188) | ❌ no klein models installed (only Z-Image) | — |

## Verified limits on the 10GB remote card (tested 2026-09-06, klein-9B Q4_K_M via unsloth images API)

- **Resolution is memory-capped for EDITS:** working memory ≈ 2GB fixed + ~7.6GB per megapixel (latents+attention can't offload). 1920×1088 needs ~18GB → refused by the pre-flight check (`estimate-memory` fires before anything allocates — good). **Max workable ≈ 960×544** on this box; upscale locally (lanczos) after download.
- `upscale` (hires-fix) is **not supported for the flux.2-klein family** — rejected at validation.
- width/height must be **multiples of 16** (1080 fails, use 1088).
- Edit latency: ~47s for 960×544 single-ref img2img on the 3080.

## Storyboard fusion recipe (char + location + prop)

1. Generate asset plates separately (Z-Image or klein T2I): character sheet, background plate, prop plate.
2. Per shot: `init_image`/first reference = the background plate (layout anchor), remaining `reference_images` = [character, prop], prompt in the official pattern: *"A photograph of <character description> from image 1 standing in the exact temple interior of image 2, holding the glowing banana from image 3, matching scale, lighting and perspective."* — at background resolution.
3. Judge identity first; reroll = same refs + new seed before touching wording.

## Additions from LTX blog FLUX.2 guide (2026-08-04, ltx.io — verified FLUX.2 family)

**Photorealism style presets** (copy-paste eras that work): modern photorealism · "2000s digicam" (saturated, casual framing) · "80s vintage photo" (warm grain, faded) · analogue film ("shot on 35mm film f/2.8, 50mm lens, Rembrandt lighting, film grain, slight desaturation") · vintage cellphone selfie.

**Camera/lens simulation table:**
- Camera models register: "Shot on Sony A7IV" / "Canon 5D Mark IV" / "Hasselblad X2D" / "Fujifilm X-T5".
- Lens: **14–24mm** dramatic wide · **35–50mm** natural versatile · **70–85mm** portrait compression · **100mm+** telephoto separation.
- Aperture: **f/1.4–2.8** shallow DoF · **f/4–5.6** balanced · **f/8–16** deep focus.
- Film stocks: Kodak Portra 400, Fuji Pro 400H, Ektachrome 64 (cross-process variants work: "expired Ektachrome 64, cyan-magenta split").

**JSON structured prompting confirmed for FLUX.2**: "FLUX.2 interprets both formats equally well — you can paste JSON directly into the prompt field." Full schema: `{scene, subjects:[{description, position, color_palette}], style, color_palette[], lighting, mood, background, composition, camera:{angle, distance, lens, f_number, iso, focus}}`. Iterate by changing ONE section. (Klein/Qwen-encoder acceptance = to test.)

**Comic-strip / sequential-art framework** (the Mongo pattern, official): per panel — Style · Character (who + action in THIS panel) · Setting · Text (quoted dialogue/captions) · Mood+lighting. Consistency rule: "Establish detailed character description in panel one… reference these exact details in every subsequent panel. Adjust only pose, expression, and action — core appearance stays locked."

**Multi-ref note:** dev endpoints commonly 6–10 refs (MP budget); "test with fewer references first, then add complexity"; specify each ref's role explicitly.

**Multilingual prompts work natively** (FR/TH/KO examples) — same structure rules apply.
