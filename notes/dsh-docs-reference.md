# DSH — official docs reference (extension / plugin / command / skill / workflow authoring)

Canonical DeepSeek Harness documentation for building extensions, plugins, slash commands, skills, and workflows. Stored here per the standing rule that any DSH automation / extension / plugin / workflow must be **documented and kept in the vault**. These are the **official docs** — consult before authoring any of the above.

- **Web base:** https://deepseek-harness.github.io/deepseek-harness/en/reference/
- **Local source (dsh checkout):** `/home/oem/Apps/deepseek-harness/docs/` — same content as markdown; web path `/en/reference/<x>` ≈ `docs/<x>.md`. Read locally when offline or to get the exact text.

## The six reference pages (user-noted, 2026-09-06)

| Topic | Web | Local source | What it covers (from the doc's own headings) |
|---|---|---|---|
| **Reference index** (landing) | https://deepseek-harness.github.io/deepseek-harness/en/reference/ | `docs/` tree | The whole reference section: `subsystems/*` + `cookbook/*`. Start here to find a topic. |
| **Human Commands** (slash commands) | https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/commands | `docs/subsystems/commands.md` | Input metadata, command definition, invocation & result, discovery/parsing views, Cordis API `ctx.commands` (`CommandRuntime`) + `commands/*` events. → the mechanism behind `/h3vfx`, `/plan`, `/compact`, `/feedback`. |
| **Extension cookbook** (plugin shapes) | https://deepseek-harness.github.io/deepseek-harness/en/reference/cookbook/extension-cookbook | `docs/cookbook/extension-cookbook.md` | Concrete plugin shapes: a tool plugin, a hook / permission-gate plugin, a UI plugin, an external protocol driver; runnable wirings; the feature→mechanism map. → fastest way to pick the right shape for a new extension. |
| **Adding a package** (workspace pkg) | https://deepseek-harness.github.io/deepseek-harness/en/reference/cookbook/adding-a-package | `docs/cookbook/adding-a-package.md` | Create the package, register it in the root configs, decide topology/naming, write the README, verify. → packaging a DSH bundle (npm `dsh.bundle.patch`). |
| **Workflow** subsystem | https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/workflow | `docs/subsystems/workflow.md` | Start request, `WorkflowMeta` identity, `WorkflowResult`, live `WorkflowRun`, failure discipline (`WorkflowError.fatal`), events, durable chat records, Cordis API `ctx.workflowEngine` + `workflow/*` events. → the multi-agent `workflow` tool. |
| **Skills** subsystem | https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/skills | `docs/subsystems/skills.md` | Provider registry, local discovery priority, skill identity, summaries/candidates/complete definitions, lookup/config, session + browser catalog & tool contract, Cordis API `ctx.sessionSkillCatalog` / `ctx.skills` + `skills/*` events. → how the `skill` tool + SKILL.md files (incl. the cordis-plugin-development snapshot) work. |

## More in the same reference tree (useful "add X" cookbooks + subsystems)
- Cookbooks: `docs/cookbook/adding-a-tool.md`, `adding-a-settings-card.md`, `adding-an-llm-adapter.md`, `adding-a-remote-api.md`, `adding-a-vendored-package.md`.
- Subsystems: `docs/subsystems/extensions.md`, `core.md`, `code-runtime.md`, `approval.md`, `permission-presets.md`, `persistence.md`, `jobs.md`, `goal.md`, `compaction.md`, `conversation.md`.

## Related vault artifacts (this repo)
- `notes/dsh-cordis-plugin-development/` — byte-for-byte snapshot of the `cordis-plugin-development` skill (dynamic Cordis plugins via the `cordis_*` tools) + its README (provenance, static-vs-dynamic distinction, by-path import lesson).

## How this maps to what we've built
- `/h3vfx` slash command (`~/.dsh/local-plugins/h3-vfx-prompt.ts`, mounted in `profiles/web/cordis.patch.yml`) → **Human Commands** + **Extension cookbook**.
- `cordis-plugin-development` skill snapshot → **Skills** subsystem.
- Multi-agent fan-out (the `workflow` tool) → **Workflow** subsystem.

## Provenance & compliance
Captured 2026-09-06 from the DSH v0.1.3-alpha.1 checkout at `/home/oem/Apps/deepseek-harness`. Text-only; no secrets/binaries/NSFW. Fits approved use #4 (durable notes).
