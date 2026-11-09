# ComfyUI: one-file drag-and-drop workflow (embedded input image) — proven 2026-11-09

Goal: give a user a SINGLE file that, dropped onto the ComfyUI canvas, loads a
full workflow AND has its input image ready — no JSON-plus-image pairing.

## Mechanism
ComfyUI reads embedded graphs from PNG metadata chunks: tEXt / iTXt / comf
(chunk reader confirmed in the remote frontend bundle: `a===tEXt||a===comf||a===iTXt`,
iTXt may be zlib-compressed; the classic form is a **tEXt chunk keyed
"workflow" containing raw JSON** — exactly what ComfyUI's own SaveImage writes,
and every frontend loads it). Dropping a PNG also copies the image into input/
under the dropped filename — so set the workflow's LoadImage widget to the
PNG's OWN filename before embedding.

## Recipe (the proven one)
1. Start from an official UI-format template (nodes+links) — patch only
   `widgets_values` (safe) and set LoadImage's value to the output PNG's name.
2. Embed with PIL **explicit PngInfo** — loose `img.info[...] = json` is NOT
   reliably written on PNG save (silent no-chunk failure proven 2026-11-09):
   `meta = PngImagePlugin.PngInfo(); meta.add_text("workflow", json.dumps(wf));
   img.save(out, format="PNG", pnginfo=meta)` then reload and assert the key.
3. Ship/SCP the PNG to wherever the user drags it. Also drop a copy into
   ComfyUI's input/ dir so Queue works even if their flow skips the upload step.

## Verification without clicking
Playwright headless on the live GUI: build a File from base64, `new DataTransfer()`,
dispatch `dragover`+`drop` on `canvas.litegraph`, then read `window.app.graph`:
remote 0.37.2 loaded 66 nodes with the LoadImage widget bound. Working reference
implementation + quality Pixal3D variants: seven-wonders repo
`game/packages/asset-replica/three-d/pipeline/` (tools/embed-workflow-png.py, ui/).

## Caveats
- Multi-image workflows (multi-view conditioning) can't embed all inputs in one
  PNG — ship JSON + place inputs in input/ yourself.
- Widget ORDER in widgets_values is node-definition order — patching an official
  template's existing arrays is safe; hand-writing arrays is not.
