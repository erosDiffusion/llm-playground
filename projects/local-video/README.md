# local-video — agent preset (verbatim)

Verbatim copy of the `local-video` DSH agent preset, archived 2026-09-06 from `$HOME/.dsh/.agent-presets/local-video/`. Runbook for the **local** ComfyUI video pipeline on port 8188: MiniMax-H3 (fl2va/ref2va) + Flux2-Klein flows, park/resume protocol around VRAM pressure, aimdo memory-control API, template usage, error triage.

## Contents

| path | what |
| --- | --- |
| `preset.yml`, `agent.cordis.yml` | preset identity + composition |
| `skills/local-video-pipeline/SKILL.md` | the full runbook (templates in `comfyui/local/`, park/resume, VRAM budget, user policies like "scripts must NOT auto-call /free") |

## Reuse

```sh
cp -r <repo>/projects/local-video "$HOME/.dsh/.agent-presets/"
```

Machine-specific facts it assumes: local ComfyUI 8188 (user-run), park scripts at `~/.dsh/bin/agent-park.sh` / `agent-resume.sh`, unsloth studio as the model manager. Adjust those paths if the box changes.
