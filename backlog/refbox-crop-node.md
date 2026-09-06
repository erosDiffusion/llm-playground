# RefBox crop/resize node (ComfyUI)

- **Type:** build
- **What:** A custom ComfyUI node to efficiently crop/resize/move (upload) an image into a user-defined box for reference use — with the ability to stack multiple similarly-cropped images. Efficiency in upload + visual transform of the image.
- **Why I want to try it:** H3 reference slots want tightly-cropped subject boxes; doing that inside the graph (instead of pre-editing files) keeps ref prep fast and repeatable across shots.
- **Fits stage:** previs→H3 (tooling; pairs with [video-frame-select-node](video-frame-select-node.md)).
- **Open questions:** box spec format (percent? px? multi-box list?); stacking = concat into a grid image or multiple ref slots?; memory efficiency for many crops at high res.
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try).
