# Prompting KB — core moviemaking tools

Per-model prompting knowledge for the studio stack. Each file: verified rules first, sources with dates, conflicts resolved, "to test" markers where knowledge is unverified. Distilled 2026-09-06 (ongoing).

## Model index

| Model | Role | Status | File |
|---|---|---|---|
| **FLUX.2 [klein] 9B/4B** | images: gen + single/multi-ref editing, storyboards | ✅ documented (7 guides cross-checked) | `flux2-klein.md` |
| **MiniMax H3** (fl2va / ref2va) | video: first-last-to-audio-video / reference-to-video | ✅ documented (BFL-style guide + toolkit, verified in production 2026-09) | `minimax-h3.md` |
| **LTX 2.3 / 2.5** | video: t2v/i2v, outpainting, HDR | ⚠️ scaffold — local assets known, prompting guide TODO | `ltx-video.md` |
| **Krea (Krea2)** | image/storyboard workflow in local studio | ⚠️ scaffold — local workflow exists, guide TODO | `krea-ideogram.md` |
| **Ideogram** | images: text-rendering specialist | ⚠️ scaffold — guide TODO | `krea-ideogram.md` |
| **Z-Image Turbo** | workhorse T2I on the 10GB remote box | ✅ recipe + behavior documented | `z-image-turbo.md` |

## Cross-model consensus (the rules that hold across the flux-family and friends)

1. **Prose over keywords.** All LLM-encoder models (klein/Qwen3, H3/Mistral-class, dev/Mistral) read natural language; keyword soup is strictly worse.
2. **Front-load the subject** — first sentence gets the most attention everywhere.
3. **Lighting is the #1 quality lever**: source + quality + direction + color temperature (+ interaction).
4. **No negative prompts on distilled/CFG-free models** (klein, Z-Image) — phrase positively; some stacks even *add* what you negate.
5. **Exact text in quotes** + font style + placement + case; treat output as layout guidance, not pixel-perfect type.
6. **HEX color codes work** across the family (describe the color alongside the code for stronger accuracy; gradients = start+end hex).
7. **Character consistency = repeat the verbatim description block in every shot**; change only pose/expression/action. (klein comic-strip rule, H3 subject_definitions, Z-Image storyboard playbook — same principle three ways.)
8. **One element at a time when iterating; fix the seed** to isolate prompt effects.
9. **Camera language is real**: lens mm, aperture, angle, film stock all register ("Shot on 35mm Kodak Portra 400, f/2.8").

## How to extend

New model → new file: CHEAT SHEET (do/don't) → verified rules with sources → conflicts resolved → hardware limits where relevant → "to test" list. Keep files text-only and <~50KB so they stay vault-publishable.
