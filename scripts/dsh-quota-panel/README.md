# dsh-quota-panel

A **Quota** panel in the DSH Web GUI (sidebar entry, order 22 — under Projects), plus the
`quota_panel` tool. It answers, before any delegation: *how much quota is left, when does it
reset, and does one more job fit?*

The point of the design: **displaying quota must never spend quota.**

## Why every number here is free

| what | where it comes from | cost |
|---|---|---|
| Antigravity pools (%) + reset timestamps | `agy -p /usage` — the CLI's **local** usage command | nothing. Measured 2026-11-01: two back-to-back reads returned byte-identical percentages (97 / 99 / 68 / 83 / 93) and no pool counter moved |
| Copilot premium requests this month | `~/.dsh/quota/acp-ledger.tsv`, appended whenever a Copilot job runs | nothing |
| Per-job prices behind the GO / NO-GO | **parsed** out of `~/.dsh/bin/acp-budget`'s `PRICE` table at read time | nothing — and the panel and the routing gate cannot drift, because the table has one owner |

The host caches the probe (`ttlMs`, default 90 s) and the client polls on a one-second tick that
only advances the **countdowns**, so keeping the tab open never re-probes the provider.

## What it shows

- **One card per pool**, split by window: a five-hour window and a weekly window expire on
  *different* timestamps, so a single "83% left" is not actionable — the countdowns and reset
  stamps are.
- **One more job — verdict per lane** against the floors the orchestrator lives by: a lane is
  **NO-GO** if one job would push a five-hour pool under 20% or a weekly pool under 25%.
- **Copilot**: premium requests used this month against a self-imposed hold (the hold is a policy,
  not the account allowance).
- **Strata**: unlimited in money; the real constraint is 2 conversation slots.

## Config (row in `cordis.patch.yml`)

`agyBin`, `ledger`, `budgetCli`, `cacheFile`, `ttlMs`, `floorFiveHour`, `floorWeekly`, `copilotHold`.

## Routes and tool

- `POST /api/quota-panel/rpc` with `{action}` ∈ `status | plan | refresh` (`plan` takes `lane`)
- `GET  /api/quota-panel/rpc?action=status&lane=opus`
- tool `quota_panel` — same three actions, same reader

## Install (this box: profile `web-lite`)

```bash
cd ~/.dsh/profiles/web-lite
# package.json: dependencies["dsh-quota-panel"] = "link:/home/oem/Apps/deepseek-workspace/dsh-quota-panel"
#               dsh.profile.bundles += "dsh-quota-panel"
pnpm install
dsh --profile web-lite --dump-config | grep -c quota-panel     # must be > 0
```

A new bundle is picked up **live** by the profile HMR watcher (it re-composes bundle patch layers),
so no GUI restart is needed — but the browser half needs a **page refresh**, since `client.js` is
static. Editing this bundle's own `cordis.patch.yml` row afterwards *does* need a restart: the
profile's own patch file is read at boot.

Predecessor: a standalone Python server on :8123 with a Projects-panel service card. Retired
2026-11-01 in favour of this bundle — one implementation, and the GUI panel the card never was.
