# scripts/dsh/ — DSH local extensions kit (survives DSH updates)

App-shell features for the DeepSeek Harness checkout that **cannot be packaged as
cordis bundles** (no extension point: e.g. `MarkdownText` props are only
text/streaming/labels/fileMentions; the composer/quote surfaces are not Slots),
so they live as standalone git patches applied on top of the upstream checkout.
This kit is the durable copy ("so I don't lose it" archive): patches + applier +
design docs. The live locations on the agent box are listed per file below.

| file | what it does | live location on the agent box |
| --- | --- | --- |
| `dsh-video-inline-chat.patch` | inline `<video controls preload="metadata">` rendering in chat markdown: image-syntax URLs with a `.mp4`/`.webm`/`.ogv` path render as a real video element (same protocol allowlist as images; relative/local/file:/javascript: stay inert alt text). Touches `packages/client/ui-primitives/src/markdown/render.tsx` (`renderImage` + `remoteVideoUrl`) + its spec | `~/.dsh/patches/dsh-video-inline-chat.patch` |
| `dsh-merge-queued-messages.patch` | composer **"merge queued messages"** toggle (switch beside the send button): while the agent is busy, a queue-mode text-only send grows the newest still-pending queued row via the existing `session.updateQueue` edit verb instead of adding a separate turn; durable `mergePending` setting (default on) in the `ui-conversation` settings namespace; 6 service tests + composer/switch UI tests | `~/.dsh/patches/dsh-merge-queued-messages.patch` |
| `dsh-quote-selection.patch` | quote surface: per-paragraph left-margin quote box (works mid-stream/thinking) + whole-message hover quote icon in the assistant strip; both open a dialog quoting visible text with turn/step/ISO-timestamp/msg-id header; Send submits quote+comment+existing draft, "To composer" stages it. New workspace package `packages/client/ui-quote` (20 files) + `ui-chat/MessageIconActions.module.css` transition split + web-app bundle row + `tsconfig.client.json` reference | `~/.dsh/patches/dsh-quote-selection.patch` |
| `apply-dsh-patches.sh` | the applier: for each patch — reverse-check (already applied → skip) → apply → `git apply --3way` fallback on drifted context → **CONFLICT exits 1 without rebuilding**; rebuild tail = `pnpm install`, `pnpm build:lib:host`, `pnpm build:lib:client`, `pnpm build:web` (pipefail — a tsc failure behind `\| tail` once shipped a stale bundle). `--install` re-syncs patches+script into `~/.dsh/` (kit layout: patches/ beside the script) | `~/.dsh/bin/apply-dsh-patches.sh` |
| `docs/dsh-merge-queued-messages.md` | design + capability notes for the merge-queued feature (dev doc) | `~/.dsh/docs/dsh-merge-queued-messages.md` |
| `docs/dsh-quote-selection.md` | design + behavior notes for the quote surface (dev doc) | `~/.dsh/docs/dsh-quote-selection.md` |

## video-scene-extractor-v2/ — bundle-skill replacement kit (2026-10-05)

Different animal from the checkout patches above: the `dsh-video-scene-extractor`
bundle (github erosDiffusion/dsh @ 7dc012c1) ships a skill whose runbook/scripts
had 12 invocation bugs (all reproduced in a live run; fixes in the kit's
`CHANGELOG.md`). The bundle hardcodes its skill path, so v2 is mounted by
**profile-patch surgery**, not a checkout patch:

| file | what it is | live location on the agent box |
| --- | --- | --- |
| `skills/video-scene-extractor/SKILL.md` + `scripts/*.py` | v2 skill: corrected runbook + 7 patched pipeline scripts (mad_scan `--quiet` + data/ layout, consolidate crash-guard + onsets.txt, extract_frames bare-number fix, montage makedirs, hashcheck raw-pipe verify mode, check_ffmpeg false-alarm fix) | `~/Apps/deepseek-workspace/dsh-video-scene-extractor-v2/skills/` |
| `plugin/index.js` | local host entry replacing the bundle row: registers `DSH_VIDEO_SKILL_DIR` + `/video-extractor` pointing at the v2 skill | `~/Apps/deepseek-workspace/dsh-video-scene-extractor-v2/plugin/` |
| `profile-patch-block.yml` | the exact block appended to the web-lite profile patch: disable bundle host row, insert v2 host row, FULL-config override of the preset row (cordis gotcha: a per-id override REPLACES the whole `config` — a partial one silently guts the preset; regeneration recipe in CHANGELOG.md) | tail of `~/.dsh/profiles/web-lite/cordis.patch.yml` |
| `CHANGELOG.md` | the 12 fixes + end-to-end proof + regeneration recipe + publish path | `~/Apps/deepseek-workspace/dsh-video-scene-extractor-v2/CHANGELOG.md` |

If the upstream bundle ever ships these fixes, delete the profile-patch block and
this kit becomes redundant. Verified via `pnpm dsh --profile web-lite --dump-config`
(2026-10-05): bundle row disabled, v2 row mounted, preset intact with v2 skill dir.

## Provenance

- Archived 2026-10-03 from the agent box (`/home/oem`), paths above. Patches in
  this copy are **regenerated against upstream base `dsh-v0.2.1-alpha.1`
  (commit `5badb15009`)** — the 2026-10-03 update (0.1.6 → 0.2.1) conflicted on
  all three patches; every conflict was resolved by hand and the staged result
  re-exported, so these patches reverse-check clean on the 0.2.1 tree and
  3-way-merge on future updates.
- No secrets in any file (scanned on archive date: 0 matches).
- Companion third-party plugin (not part of the patch kit): **`dsh-qwen38-local-qol`
  v0.3.2** by Yunado (https://github.com/Yunado/dsh-qwen38-local-qol) — maps the
  local NInfer vision patch-budget 400 ("vision raw patches exceed processor
  budget") onto `CONTEXT_WINDOW_EXCEEDED` so the harness overflow recovery
  compacts + retries, and declares the `qwen38` agent preset (custom compaction
  backend, model route `localhost:8080/v1` llamacpp dialect = local NInfer).
  Installed per-profile: `dsh plugin --profile <name> add github:Yunado/dsh-qwen38-local-qol#v0.3.2`
  (v0.3.2 = current tag as of 2026-10-03; README compat: host ≥ 0.2.0-rc.2 →
  `#v0.3.2`, host ≤ 0.1.6-alpha.2 → `#v0.2.0`). It is a normal profile dependency
  (survives checkout updates untouched) — but re-check the tag after big
  upstream releases.

## Update protocol (after ANY DSH checkout update)

1. `cd /home/oem/Apps/deepseek-harness && git pull --ff-only` (or tag checkout / re-clone).
2. `bash ~/.dsh/bin/apply-dsh-patches.sh` — idempotent; expect clean skip on the
   current base, 3-way auto-merge on small drift, or CONFLICT (exit 1) on big
   drift. On CONFLICT: resolve by hand (keep upstream structure, splice the
   feature in), `git add` the resolved files, then run the rebuild tail manually
   (the script refuses to build on conflict).
3. Re-verify: `node --import tsx/esm apps/cli/src/bin.ts --profile web-lite --dump-config`
   (expect `qwen38` + `preset-qwen38` rows + the local plugins), and grep the
   built artifacts for feature markers:
   - merge-queued: `grep -c mergePending packages/client/ui-conversation/lib/client.js`
   - quote: `grep -c 引 packages/client/ui-quote/lib/client.js`
   - video: `grep -c ogv apps/web/dist/assets/index-*.js`
4. **Refresh this vault copy**: if any patch was re-merged by hand, regenerate
   it from the staged worktree diff (per scope: `git diff --cached -- <paths> >
   ~/.dsh/patches/<patch>`) and update the copies here (same gh-git worktree
   flow), with the new upstream base commit recorded above. Verify each patch
   with `git apply -R --check`.
5. Restart the GUI host (user-managed): kill the `dsh` web process, relaunch
   `node --import tsx/esm apps/cli/src/bin.ts --profile web-lite`, refresh the
   browser page.

### 0.1.6 → 0.2.1 drift points (resolved 2026-10-03; reuse as a map for the next drift)

- **`ui-conversation` (merge-queued)**: 0.2.1 refactored composer/queue:
  `SessionSnapshot.queue` is gone — queue rows now live in the **Agent Inbox
  projection** (`session.projections.faceOf('inbox').getSnapshot()` →
  `InboxState['next-turn']` = `UserMessage[]`; steering/context rows are
  `next-step`). `mergeIntoQueue` was rewritten onto that (text-only target
  check = all content blocks are text; write path `session.updateQueue`
  unchanged). Settings: `SettingsScope` → `ConfigForm` (host forms refactor,
  #4587) — `ComposerSubmissionPolicy` host field + test stubs
  (`stubSettingsScope` → `stubConfigForm`, publish needs
  `status:'ready'`/`writable:true`). InputBar gained the activity/
  standardControls trailing layout + `useStopShortcut`; the merge switch was
  spliced between `standardControls` and the activity div.
  `host.client.spec.ts` was restructured upstream (the mergePending settings
  assertion moved into `config.host.spec.ts`).
- **`ui-quote`**: `tsconfig.json` project references — packages that moved to
  solution-shells (`ui-chat`, `ui-conversation`, `locale`) must be referenced by
  per-face file (`../x/tsconfig.client.json`), not by directory.
- **`web-app/package.json`**: upstream rewrote the whole dependency block
  (`workspace:^` → `workspace:*`, new packages) — merge = keep the upstream
  block + insert the `dsh-client-ui-quote` line alphabetically.
- **`pnpm-lock.yaml`**: take the upstream version; the rebuild's `pnpm install`
  regenerates workspace entries.
- **Stale untracked package dirs** (e.g. `packages/settings/settings-file/`,
  old `e2b/*`, `code-runtime/*`, `tool-present` under `packages/fs/`) from the
  pre-update build break `build:lib:host` (tsdown globs `packages/*/*` and
  bundles their stale `lib/types/*.js` against the new sources). Remove them
  (they are untracked build residue; the new `tool-present` lives at
  `packages/deliverables/tool-present`).

## Budget note (why the qwen38 plugin matters here)

Local NInfer serves Qwen3.8-27B with a hard vision budget: 1 token = 32×32 px,
131,072 raw patches (32,768 tokens) per prompt, 16,384 tokens per image, frames
≤16 MP are not downscaled (artifact preprocessor config `longest_edge: 16777216`).
Without the plugin, that 400 is classified `INVALID_REQUEST` (non-retryable) and
kills the turn. With it, the same 400 becomes `CONTEXT_WINDOW_EXCEEDED` →
overflow recovery compacts (compaction backend strips images to text) and
retries. Rule of thumb while authoring vision work: ≤~10–12 full-size frames per
session (3200×1165 ≈ 14,400 patches; 1276×718 ≈ 3,520), analysis frames ≤1280px
wide (~2,300 patches), per-frame analysis in subagents.
