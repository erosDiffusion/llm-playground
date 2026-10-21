Archived 2026-10-21 from machine path `$HOME/Apps/deepseek-workspace/dsh-strata-flex` (live install: `link:` bundle in the `web-lite` profile). Provenance: authored in-session 2026-10-21, route + flex protocol verified live against the Strata engine.

# dsh-strata-flex

Two footer buttons in the DSH Web GUI (composer dock, next to the merge-pending
control) that flex the **Strata agent engine's elastic expert cache**:

- **⬇ lower brain** — `reserve_mib: 22016` → ~512 experts resident, engine ~10 GB, ~20 GB freed for local ComfyUI work (H3 / klein / DLSS-Wine).
- **⬆ reclaim** — `reserve_mib: null` → engine start reserve (2048), full-speed agent.
- The dotted pill shows live state (`experts resident/total · free VRAM`) from `GET /metrics`; click to refresh.

How: the browser POSTs only to the plugin's same-origin route `/api/strata-flex`
(`src/index.js`), which calls the Strata engine over node:http **without an Origin
header** — the engine's own-origin guard accepts that (browser-origin calls are
rejected 403 unless added to the engine's `trusted_origins`). The engine applies
flex between requests (it can wait up to 300 s if the agent is mid-request — the
button just waits).

Protocol owner: `~/.dsh/AGENTS.md` "Strata flex protocol". API details:
`llm-playground/scripts/strata-vram-flex.md`.

Installed into the `web-lite` profile as a `link:` bundle (2026-10-21).
After changing `client.js` a browser page refresh is required (no HMR watcher
running for web artifacts).

## Surviving DSH updates

The bundle is a `link:` in the profile — it lives in `~/.dsh/profiles/` and in
this workspace folder, both untouched by harness updates/re-clones. Checklist
after any DSH update:

1. `curl -s http://127.0.0.1:3080/api/strata-flex/state` → JSON = host half still mounted.
   If it 401s ("unauthorized") the route is missing: check
   `dsh --profile web-lite --dump-config | grep strata-flex` (row present?) and that
   `~/.dsh/profiles/web-lite/node_modules/dsh-strata-flex` resolves; if it dangled,
   re-run `pnpm install` in the profile dir and nudge reconcile with a comment line in
   `web-lite/cordis.patch.yml` (a plain touch hits the bundles-unchanged early return).
2. Reload the browser page. The React path uses the `conversation.composer.dock`
   slot; if a harness update renames that internal, `client.js` automatically falls
   back to plain-DOM injection into `[data-composer-dock]` (stable data-attribute).
   Console shows `[dsh-strata-flex] slot API unavailable…` when the fallback fires.
3. Source of truth archived in the vault: `llm-playground/projects/dsh-strata-flex/`
   (restore = copy back + re-add the two `package.json` entries + `pnpm install`).
