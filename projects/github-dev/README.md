# github-dev — agent preset (verbatim)

Verbatim copy of the `github-dev` DSH agent preset, archived 2026-09-06 from `$HOME/.dsh/.agent-presets/github-dev/`. Standard coding agent + scoped GitHub access: every github.com git operation through the `gh-git` wrapper (fine-grained PAT injected per call, allowlist enforced), commit identity from config.

## Contents

| path | what |
| --- | --- |
| `preset.yml`, `agent.cordis.yml` | preset identity + composition (persona paragraph with the GitHub hard rules, skill mount) |
| `skills/github-dev/SKILL.md` | full runbook: token hygiene, scope enforcement, setup steps for PAT minting, troubleshooting |

## Reuse

```sh
cp -r <repo>/projects/github-dev "$HOME/.dsh/.agent-presets/"
```

**Not included (by design — see repo AGENTS.md):** the token (`~/.dsh/github/token`), the scope config (`~/.dsh/github/config.json`), and the `gh-git` wrapper itself (archived in `scripts/`). On a new machine: restore those three, mint a fine-grained PAT scoped to your repos, set commit identity — the SKILL.md Setup section walks through it.
