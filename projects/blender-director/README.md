# blender-director — agent preset (verbatim)

Verbatim copy of the `blender-director` DSH agent preset, archived 2026-09-06 from `$HOME/.dsh/.agent-presets/blender-director/`. Drives Blender 5.1.2 via MCP: description → shot list → per-frame bake → headless render → ffmpeg mp4; Workbench flat-color minimal default; every export gets a cued `.md` + H3 full-reference prompt (`-cues-h3.md`); artifacts in `generated/movies/<YYYY-MM-DD>/<scene-name>/`.

## Contents

| path | what |
| --- | --- |
| `preset.yml`, `agent.cordis.yml` | preset identity + composition (persona, tool realm, skill mount) |
| `skills/blender-director/SKILL.md` | the full runbook (rules v2/v3/v4, export protocol, asset-folder layout) |
| `skills/blender-director/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md` | MiniMax-H3 reference-mode prompt guide (source HF `MiniMaxAI/MiniMax-H3`) — the format behind `-cues-h3.md` |
| `reference/alley_corner_chase.py` | **canonical** reference scene script (8 shots, whip pan, OTS, per-frame bake) — copy its structure for new scenes |
| `reference/weather_time_dialogue.py` | older richer-look scene (EEVEE + sky) — reuse shot-table/bake mechanics only |

## Reuse

```sh
cp -r <repo>/projects/blender-director "$HOME/.dsh/.agent-presets/"
```

then pick "Blender Director" in the session picker. Note: `SKILL.md` references this machine's Blender binary path and the workspace reference scripts (`/home/oem/Apps/deepseek-workspace/blender-director/*.py`); on another machine restore those paths (the copies in `reference/` are the source) or edit the two lines in SKILL.md.
