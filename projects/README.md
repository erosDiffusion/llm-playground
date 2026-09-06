# projects/ — standalone mini-projects & reusable packages

Self-contained source experiments and packaged capabilities: one project per folder, each with its own short README (what it is, how to run/reuse it). Source + text only — no binaries, no large assets (see `../AGENTS.md`).

## Index

| project | what it is | reuse |
| --- | --- | --- |
| [h3-prompt-toolkit](h3-prompt-toolkit/) | MiniMax-H3 **fl2va** prompt toolkit: character-pool builder + scene-grammar validator (incl. measured-banned camera phrases) + full format spec | run the scripts directly; spec is reference |
| [blender-director](blender-director/) | agent preset: direct Blender 5.1.2 via MCP (description → shots → bake → render → mp4, cued `.md` + H3 reference prompts) + canonical reference scene scripts | `cp -r` to `~/.dsh/.agent-presets/` |
| [github-dev](github-dev/) | agent preset: scoped GitHub access via the `gh-git` wrapper (token hygiene + allowlist runbook) | `cp -r` to `~/.dsh/.agent-presets/` (+ restore token/config/wrapper — see its README) |
| [local-video](local-video/) | agent preset: local ComfyUI 8188 video pipeline runbook (H3 fl2va/ref2va, park/resume, aimdo memory control) | `cp -r` to `~/.dsh/.agent-presets/` |
| [dsh-customizations](dsh-customizations/) | the DSH harness layer: `system-stats` + `mcp-gateway` host plugins, inline-video chat patch (the profile composition itself is documented, not copied — private endpoint) | restore per its README |

Standing rule (user, 2026-09-06): **anything we build that is reusable — cordis presets/agents, skills, local plugins, harness patches — gets packaged here** so it survives machine loss and can be re-deployed from the repo. New artifacts: add a folder + index row in the same commit.
