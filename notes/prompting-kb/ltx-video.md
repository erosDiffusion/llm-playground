# LTX 2.3 / 2.5 — video prompting

⚠️ SCAFFOLD (2026-09-06) — local assets known; official prompting guide NOT yet distilled (ltx.io blog has tutorials + docs.ltx.video; the guessed `/blog/ltx-prompting-guide` URL 404s).

## What we have locally (verified in workspace AGENTS.md)

- Local ComfyUI studio: **LTX 2.3 / 2.5** (dev + distilled int8-convrot variants) + VAEs + upscalers — full pipeline on the local box (park first; see `local-video-pipeline` skill).
- LTX ecosystem capabilities (from ltx.io nav, unverified locally): image-to-video, world model, LoRA training, HDR video, outpainting.
- Cross-model consensus (README) applies as a baseline until the official guide is distilled: prose, subject-first, lighting explicit, camera language real.

## TODO

- [ ] Distill ltx.io tutorials/blog prompting pages (find correct URLs via /blog index)
- [ ] Verify shot/camera vocabulary acceptance vs H3's fixed list
- [ ] Local test pair (t2v + i2v) once parked — same generate→edit matrix protocol as klein
