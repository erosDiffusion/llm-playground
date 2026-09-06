# backlog/ — things I want to try

Durable wishlist of external repos, tools, and experiments worth trying — with status and *why* they matter. Ideas arrive in chat sessions and would otherwise be lost; this section is where they persist (see `../AGENTS.md`). Eventually most items become real projects — in `projects/` here or on the local machine.

## North star (why these exist)

**Drive MiniMax H3 (local ComfyUI :8188) with video produced in Blender.**

Flow: text description → agent builds the scene + camera move in Blender (existing `blender-director` preset) → render a white-model previs → feed previs + first frame + prompt into H3 as motion/look reference. Camera control is ideally **user-driven** — phone, gamepad, or gesture (nothing attached yet) — so shots can be iterated interactively instead of re-rendered blind.

| Stage | Status today | Candidate(s) here |
|---|---|---|
| Description → Blender scene + camera move | ✅ have it | `blender-director` preset (workspace, not this repo) |
| Preset actions/camera moves → v2v flow | ⬜ core experiment | [preset-action-movies-v2v](preset-action-movies-v2v.md) |
| Motion control into H3 | ⬜ untested | [h3-controlnet-test](h3-controlnet-test.md), [blender-shot-video](blender-shot-video.md) (recipe ref) |
| User-driven camera control (phone/gamepad/gesture) | ⬜ missing | [blender-camera-controller](blender-camera-controller.md), [blender-handcontrol-ar](blender-handcontrol-ar.md) |
| ComfyUI tooling (nodes) | ⬜ building | [pose-camera-library-node](pose-camera-library-node.md), [video-frame-select-node](video-frame-select-node.md), [refbox-crop-node](refbox-crop-node.md), [test-custom-node-flows](test-custom-node-flows.md) |
| Content sourcing / styles | ⬜ exploring | [vfx-from-references](vfx-from-references.md), [sketch-drawing-animation](sketch-drawing-animation.md), [sam3d-body-poses](sam3d-body-poses.md) |
| Post-processing (upscale) | ⬜ exploring | [dlss5-video-upscale](dlss5-video-upscale.md) |
| H3 speed / VRAM headroom | ⬜ optional | [minimax-h3-turbo](minimax-h3-turbo.md), [vsa-pdd-acceleration](vsa-pdd-acceleration.md) |
| Infra / meta (delegation, infra skills, engines) | ⬜ various | [multiagent-3080-delegation](multiagent-3080-delegation.md), [banodoco-integration](banodoco-integration.md), [k8s-podman-knowledge](k8s-podman-knowledge.md), [backend-engines-comparison](backend-engines-comparison.md), [dflash2-feasibility](dflash2-feasibility.md), [kanban-board](kanban-board.md) |
| **Ship it** | ⬜ | [movie-pipeline-finish](movie-pipeline-finish.md) |

## Index (canonical list — keep in sync with entry files)

| Item | Type | Fits stage | Status |
|---|---|---|---|
| [preset-action-movies-v2v](preset-action-movies-v2v.md) | build | core loop | want-to-try |
| [blender-shot-video](blender-shot-video.md) (Yi-111-a) | external | recipe ref | want-to-try |
| [h3-controlnet-test](h3-controlnet-test.md) | test | motion control | want-to-try |
| [sam3d-body-poses](sam3d-body-poses.md) | explore | content→scene | want-to-try |
| [pose-camera-library-node](pose-camera-library-node.md) | build | tooling | want-to-try |
| [video-frame-select-node](video-frame-select-node.md) | build | tooling | want-to-try |
| [refbox-crop-node](refbox-crop-node.md) | build | tooling | want-to-try |
| [test-custom-node-flows](test-custom-node-flows.md) | test | tooling QA | want-to-try |
| [dlss5-video-upscale](dlss5-video-upscale.md) | explore | post-processing | want-to-try |
| [vfx-from-references](vfx-from-references.md) | explore | content sourcing | want-to-try |
| [sketch-drawing-animation](sketch-drawing-animation.md) | explore | content | want-to-try |
| [movie-pipeline-finish](movie-pipeline-finish.md) | integrate | all (ship it) | want-to-try |
| [blender-camera-controller](blender-camera-controller.md) (garuh143) | external | user camera | want-to-try |
| [blender-handcontrol-ar](blender-handcontrol-ar.md) (Dotrealm-dev) | external | user camera (gesture) | want-to-try |
| [minimax-h3-turbo](minimax-h3-turbo.md) (Yi-111-a) | external | H3 speed | watch |
| [vsa-pdd-acceleration](vsa-pdd-acceleration.md) | explore | H3 speed | want-to-try |
| [multiagent-3080-delegation](multiagent-3080-delegation.md) | integrate | infra | want-to-try |
| [banodoco-integration](banodoco-integration.md) | integrate | workflow glue | want-to-try |
| [k8s-podman-knowledge](k8s-podman-knowledge.md) | know-how | infra | want-to-try |
| [backend-engines-comparison](backend-engines-comparison.md) | explore | infra | want-to-try |
| [dflash2-feasibility](dflash2-feasibility.md) | explore | infra (agent LLM) | want-to-try |
| [kanban-board](kanban-board.md) | build | infra | want-to-try |

Types: `external` = try someone else's repo/tool · `build` = build it locally · `explore` = study/experiment · `test` = validate what we have · `integrate` = wire things together · `know-how` = skill building.

## Procedure (how this tracker works)

**Source of truth:** one entry file per item in this folder + the index table above. The table is the at-a-glance view; entry files hold detail and the dated status log. They must stay in sync — when one changes, change both in the same commit.

**Add an item:**
1. Create `<kebab-slug>.md` with the standard shape: `Type` · `What` · `Why I want to try it` · `Fits stage` · (optional) `Open questions` / `Related` · `## Status log` starting with `- <date> — added to backlog (<status>).`
2. Add a row to the index table above (status = `want-to-try`, or `watch` for lower-priority/monitoring).
3. Commit `backlog: add <slug>` and push via gh-git.

**Update an item:** edit the entry file, append a dated line to its status log, update the table's status cell if it changed. Commit `backlog: <slug> → <new-status>` (or `backlog: update <slug>` for detail-only edits).

**Statuses:** `want-to-try` → `investigating` (reading code/docs) → `trying` (running/experimenting) → `integrated` (folded into the local pipeline — record *where*) or `dropped` (record the reason in the log). `watch` = parked, revisit when something else lands.

**Project pointer:** when an item moves to `trying`, its working code goes in `projects/<slug>/` here or on the local machine, and the entry file gets a `Working at:` pointer line so future sessions find it.

**Delegation:** bulk bookkeeping (many status updates, index rebuild, adding a batch of items) may be delegated to a subagent with this README as its spec; content decisions (what to try, priorities, drops) stay with the main session/user.
