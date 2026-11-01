# Strata VRAM slider — feasibility (research 2026-11-01)

Goal: turn the GUI "⬇ lower brain" fixed action into a `reserve_mib` slider.
Verdict: already 90 % built as a workspace bundle; a small edit — no harness change.

**Status 2026-11-01: BUILT.** `action: "set"` on `/api/strata-flex` plus a hover
slider on the footer button. The route owns the guard — clamp to 2048..22016,
snap to the engine's 512 MiB resize segment, refuse reclaim while ComfyUI reports
a busy queue — and `dry_run: true` answers the clamped value WITHOUT touching the
engine, which is how it was tested (verified: 40000 → 22016, 12000 → 11776,
9000 → 9216; engine state unchanged in every dry run).

## What exists today

The control is NOT in the harness: `grep` for `vram|reserve_mib|flex` over
`deepseek-harness/{apps/web,packages}` → zero matches. What the user clicks
is the **`dsh-strata-flex` bundle**, mounted live in the `web-lite` profile
(`~/.dsh/profiles/web-lite/package.json`: `link:` dep + bundles row, live reload).

- Host half `dsh-strata-flex/src/index.js:80-85` registers the same-origin
  route `/api/strata-flex`; the browser never talks to the engine directly.
- Today's value is a **fixed config constant**: `cordis.patch.yml:17-19`
  (`flex_reserve_mib: 22016`, `busy_reserve_mib: 14336`); `src/index.js:111-124`
  maps `action: flex|busy|reclaim` → `22016 | 14336 | null` and POSTs the
  engine (`:126`, 310 s timeout).
- Client half `client.js:95-97` injects React buttons into the composer-dock
  slot; `:105-150` DOM fallback into `[data-composer-dock]` if a harness
  update renames the slot. A live dotted pill already probes state (`:82`).
- Second surface: `projects-panel.json:135-153` card buttons POST the same
  route; `:205` watchOnly Strata card. `GET :3080/api/strata-flex/state` →
  `ok:true` + `config:{floor:22016,busy:14336}` (probe 2026-11-01).

## Why a bundle not a harness edit

The bundle rides three documented seams; updates never touch workspace dirs:

- `dsh.profile.bundles` — each profile `package.json` entry resolves to its
  patch layer in order (`packages/boot/app-boot/src/profile.ts:777`,
  `apps/cli/src/profile-boot.ts:3`); `link:` deps survive re-clones.
- `webServer.register` — `packages/host/webserver/src/index.ts:366`
  (returns a disposer), `'exact'|'prefix'` at `:43-44`, longest-prefix
  dispatch `:542-549`; shipped use: `open-in-app/src/index.ts:193`.
- `slots.inject` — rule at
  `packages/extensions/cordis-client-runner/src/client/slot-catalog.ts:69-70`;
  dock slot declared `packages/client/ui-conversation/src/client/contract/slots.ts:274`,
  rendered `.../skeleton/InputBar.tsx:543-545`. Client js is discovered from
  `dsh.client` + `exports["./client"]` (`packages/client/modules/src/index.ts:2-3,868`).

So: slider = edit `client.js` + extend the route's action map.

## v0 spec

- Route (existing): `POST /api/strata-flex` `{"action":"set",
  "reserve_mib":N}` → validate → engine `POST /v1/vram`. Response unchanged:
  `{ok, action, state:{reserve_mib, expert_slots, expert_cache_mib,
  vram_free_mib}}` (already built at `src/index.js:59-68`).
- Slider: **2048–22016 MiB, step 512** (= the engine's resize segment,
  `Strata/serve/server.py:3206-3210`). Label `keep <N/1024> GiB free` plus
  live `experts X/9645 · Y GiB free` from the response.
- Persist the slider in browser `localStorage`; patch.yml keeps floor/busy presets.
- The two buttons the user wants **already exist**: ⬆ reclaim sends
  `reserve_mib:null`; probe is the dotted pill (`GET /api/strata-flex/state`).
  Only the slider + `action:"set"` are new work.

## Safety envelope

Engine side (sources `~/Apps/Strata/serve/`, probed 2026-11-01):
- `/v1/vram` accepts any **integer ≥ 0 or null**, else 400 (`server.py:7313-7315`);
  foreign `Origin` → 403; mid-request → 409 `ModelBusy` after waiting up to
  300 s at a request boundary (`server.py:4516-4531`). The engine enforces
  **no floor — the route must**.
- Box numbers (probe 2026-11-01: `curl -s :8080/metrics | jq .engine`,
  `nvidia-smi --query-gpu=memory.total,memory.free`): total 32,607 MiB;
  full cache 9,645 slots ≈ 18,734 MiB; free 1,933 (engine) / 1,614 (driver);
  start reserve 2048 (`strata-iq3_s.json`). Proven ceiling: reserve 22,016 →
  ~512 experts, ~19,369 free (probe 2026-10-31, `~/.dsh/AGENTS.md`).

Route must enforce what the engine won't:
- Clamp `set`: `2048 ≤ N ≤ 22016`, `N % 512 == 0`, else 400.
- Block reclaim / big slider while ComfyUI runs: `GET :8188/queue_prompt` →
  refuse if `queue_running`+`queue_pending` non-empty; offer busy 14336.
  Unreachable ComfyUI = "not running" (it was down at probe 2026-11-01).
- Never kill/restart the engine/sidecar: bundle does only `GET /metrics` +
  `POST /v1/vram` — keep it that way (no subprocess).
- Too-high N starves the cache (agent streams experts from RAM); values above
  the proven 22,016 stay unexposed until probed.

## Open questions

- Anything above 22,016 safe? Untested — probe idle with
  `{"reserve_mib":24576}`, read response, then widen.
- Persist slider via `localStorage` (proposed) vs patch.yml? Busy-guard: only
  local `:8188`? Make it a bundle config key.
- Unauthenticated localhost GET on the route answered 2026-11-01 — check
  whether DSH gates `/api/*` by session token (flex already exposed today).
- Dock space is tight: slider in the `ext-strata-flex` card; dock keeps buttons + pill.
