# backlog/ — things I want to try

Durable wishlist of external repos, tools, and experiments worth trying — with status and *why* they matter. Ideas arrive in chat sessions and would otherwise be lost; this section is where they persist (see `../AGENTS.md`).

## North star (why these exist)

**Drive MiniMax H3 (local ComfyUI :8188) with video produced in Blender.**

Flow: text description → agent builds the scene + camera move in Blender (existing `blender-director` preset) → render a white-model previs → feed previs + first frame + prompt into H3 as motion/look reference. Camera control is ideally **user-driven** — phone, gamepad, or gesture (nothing attached yet) — so shots can be iterated interactively instead of re-rendered blind.

| Stage | Status today | Candidate(s) here |
|---|---|---|
| Description → Blender scene + camera move | ✅ have it | `blender-director` preset (workspace, not this repo) |
| User-driven camera control (phone/gamepad/gesture) | ⬜ missing | [blender-camera-controller](blender-camera-controller.md), [blender-handcontrol-ar](blender-handcontrol-ar.md) |
| Previs render → H3 input (first frame + motion ref) | ⬜ untested flow | [blender-shot-video](blender-shot-video.md) documents the exact recipe |
| H3 speed / VRAM headroom | ⬜ optional | [MiniMax-H3-Turbo](minimax-h3-turbo.md) |

## Index

| Item | What it is | Fits stage | Status |
|---|---|---|---|
| [blender-shot-video](blender-shot-video.md) (Yi-111-a) | Blender white-model previs → any AI video model | previs→H3 | want-to-try |
| [MiniMax-H3-Turbo](minimax-h3-turbo.md) (Yi-111-a) | Standalone H3 acceleration layer, no ComfyUI | H3 speed | watch |
| [blender-camera-controller](blender-camera-controller.md) (garuh143) | Phone/gamepad camera control over LAN | user camera | want-to-try |
| [blender-handcontrol-ar](blender-handcontrol-ar.md) (Dotrealm-dev) | Hand-gesture camera control via phone + MediaPipe | user camera | want-to-try |

## Format & statuses

One file per item, kebab-case name. Each entry: link · what it is · why I want to try it · how it fits the north star · open questions · status log (dated lines, newest first).

Statuses: `want-to-try` → `investigating` (reading code) → `trying` (running/experimenting) → `integrated` (folded into the pipeline) or `dropped` (reason recorded in the log).
