# cordis-plugin-development — skill snapshot (durable vault copy)

A **byte-for-byte snapshot** of the DeepSeek Harness `cordis-plugin-development` skill, stored here so it survives a `git pull` / update on the dsh repo. The canonical copy lives *inside* that repo and can move or change on an update; this file is self-contained (no symlinks, no pointers back to the checkout), so it keeps working regardless of the dsh repo's state.

## Provenance
- **Source:** `packages/preset/agent-presets/presets/cordis/skills/cordis-plugin-development/SKILL.md` in the dsh repo (local checkout at `/home/oem/Apps/deepseek-harness`).
- **dsh version:** `dsh-v0.1.3-alpha.1` (commit `d347e70390`).
- **Copied:** 2026-09-06. Verified byte-identical to the source at copy time (`diff -q` → identical).
- **Re-sync:** after any dsh update, re-copy from the source path above (same filename) and bump the version/commit + date here. This is a *snapshot*, not a live link — that is the point.

## What it covers
Authoring **dynamic Cordis Plugins** — the session-scoped, in-memory packages driven by the `cordis_*` tools (`cordis_inspect_list` / `cordis_inspect_query` / `cordis_inspect_self` / `cordis_define` / `cordis_run` / `cordis_stop` / `cordis_undefine`). Host vs Client halves, the plain-JavaScript constraint (no TS / JSX / import), `ctx.get` vs `inject`, side-effect cleanup (`ctx.on` / `ctx.effect`), Slot & theme UI, timers, Host↔Client RPC (`harness.handle` / `host.call`), dynamic model Tools, and the version/approval/repair flow.

## Use it for / not for (important)
- **Use when** the capability should be a *temporary, session-scoped* extension of the running harness — a browser UI in a Slot, a Host service/tool that only needs to live for this session, or anything you'd drive with `cordis_define` / `cordis_run`. Also fine as a general reference for Cordis authoring conventions.
- **Not the mechanism for** *persistent* plugins mounted into a composition: a by-path plugin in `~/.dsh/local-plugins/*.ts`, or a row in a profile/preset `cordis.patch.yml`. That is a different, disk-based mechanism — see the `editing-cordis-compositions` skill and the workspace AGENTS.md section **"DSH plugin authoring & ecosystem"**. Examples of that static path: the `/h3vfx` slash command and the `system_stats_local` tool (both are by-path plugins mounted via `profiles/web/cordis.patch.yml`).

## Hard-won lesson — by-path local plugins
A by-path local plugin in `~/.dsh/local-plugins/` lives **outside the pnpm workspace tree**, so Node **cannot resolve bare `@deepseek-ai/*` specifiers** from there — only builtins and type-only imports (erased at runtime) work. Importing e.g. `createUserMessage` from `@deepseek-ai/dsh-llm` fails boot with `MODULE_NOT_FOUND`. Fix: build the value inline (e.g. a user message as `{ id, role:'user', content, source }` using `node:crypto.randomUUID()`). Verify a by-path plugin loads from its *real* location before relying on it:

```
node --import tsx/esm --input-type=module -e "await import('<abs path to the .ts>')"
```

## Repo compliance
Text-only markdown; no secrets, binaries, video, or NSFW content. Fits approved use #4 (gists / snippets / durable notes).
