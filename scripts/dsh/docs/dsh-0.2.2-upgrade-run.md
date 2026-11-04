# DSH Upgrade Run: v0.2.1-rc.2 -> v0.2.2-rc.1

Execution Date: 2026-11-04  
Operator: Subagent (automated upgrade protocol)  
Live Base: `dsh-v0.2.1-rc.2` (`687f282e8625c6b8d11ff58211a90524be2e4317`)  
Target Ref: `dsh-v0.2.2-rc.1` (`66491b05e3f05ad35bcdd4f6cd7ed26041d9e3db`)  
Gap: 2,642 commits  
Repo: `/home/oem/Apps/deepseek-harness`

---

## 1. Executive Summary & Verification Matrix

All 5 local patch kits were re-merged against `dsh-v0.2.2-rc.1` in an isolated scratch worktree (`/tmp/dsh-up`).
Each kit was regenerated into `/tmp/dsh-up/kit-v2/<name>.patch`, and cleanly verified with both forward application and reverse check (`git apply -R --check`).
The entire build toolchain succeeded with exit code 0 (`pnpm build:lib:host`, `pnpm build:lib:client`, `pnpm build:web`), and 33 test spec suites covering 852 unit and integration tests passed cleanly (0 failed).

| Kit Name | Conflicted Files / Real Cause | Re-merge Resolution | Reverse-Apply Verified | New Patch Size |
|---|---|---|---|---|
| `dsh-acp-subagent-running.patch` | Context drift in `packages/api/session-controller/src/index.ts` due to upstream model catalog refactoring (`buildModelCatalog` moved to `catalog.ts` but re-imported in `index.ts`). | Applied via 3-way merge cleanly into target `index.ts` (lines 234 & 646), `subagent/index.ts`, and `subagent/manager.ts`. | Clean (`git apply -R --check` OK) | 4.2 KB (4,178 bytes) |
| `dsh-merge-queued-messages.patch` | Upstream PR #6426 / composer image upload pre-flight (`c29fdd3bf6`, `317e56d108`, `af4bddbc59`, `84edeadc2b`). Slots interface added `mergePending`, `service.ts` modified `sendSession` signature, `InputBar.module.css` hover query needed touch-hover guard, and 6 new locale dictionaries (`ja`, `es`, `fr`, `de`, `ru`, `pt`) required `'input.mergePending'`. | Re-anchored `mergeIntoQueue` before attachment submission, updated `InputBar` props & tooltips (`portal` attribute for fixed composer container), added `@media (hover: hover)` guard, populated all locale dicts. | Clean (`git apply -R --check` OK) | 43 KB (43,261 bytes) |
| `dsh-mermaid-chat.patch` | Context shift in `packages/client/ui-primitives/package.json` and `render.tsx` around code block rendering. | Applied cleanly via 3-way merge; preserves dynamic import of `mermaid` 11.17.2, SVG sanitize/dom-to-react, and settled-fence rendering. | Clean (`git apply -R --check` OK) | 17 KB (16,613 bytes) |
| `dsh-quote-selection.patch` | `actions.module.css` and `paragraph.module.css` failed new `hover-styles.client.spec.ts` rule (`@media (hover: hover)` required for client CSS). | Wrapped `.action:hover` and `.box:hover` in `@media (hover: hover)` blocks. New package `packages/client/ui-quote` and `cordis.patch.yml` wire seamlessly into `0.2.2-rc.1`. | Clean (`git apply -R --check` OK) | 76 KB (77,344 bytes) |
| `dsh-video-inline-chat.patch` | `render.tsx` docstring and test file drift in `tests/markdown.client.spec.tsx` (upstream added raw HTML omission tests). | Re-anchored video extension regex (`.mp4`, `.webm`, `.ogv`) and `remoteVideoUrl` handler alongside `MermaidBlock`. Added unit tests for video URL neutralization. | Clean (`git apply -R --check` OK) | 5.2 KB (5,233 bytes) |

---

## 2. Build & Spec Test Results

### 2.1 Builds
- `pnpm build:lib:host`: **EXIT 0** (36 Typert artifacts, host tsdown & rolldown bundles generated in 3.3s + 52ms)
- `pnpm build:lib:client`: **EXIT 0** (client tsdown & rolldown bundles generated across all client modules without TS errors)
- `pnpm build:web`: **EXIT 0** (Vite production web bundle built in 5.69s)

### 2.2 Spec Suites Covering Kit Domains
Executed on `/tmp/dsh-up`:
- `packages/subagent/subagent/tests/out-of-process.spec.ts`: 10 passed (10)
- `packages/subagent/subagent/tests/external-activation.spec.ts`: 19 passed (19)
- `packages/subagent/subagent/tests/external-lifecycle.spec.ts`: 7 passed (7)
- `packages/subagent/subagent/tests/run-settlement.spec.ts`: 2 passed (2)
- `packages/api/session-controller/tests/controller.host.spec.ts`: 8 passed (8)
- `packages/client/ui-primitives/tests/markdown.client.spec.tsx`: 39 passed (39)
- `packages/client/ui-primitives/tests/mermaid.client.spec.tsx`: 5 passed (5)
- `packages/client/ui-conversation/tests/service-orchestration.client.spec.ts`: 52 passed (52)
- `packages/client/ui-conversation/tests/input-bar.client.spec.tsx`: 140 passed (140)
- `packages/client/ui-conversation/tests/submission-policy.client.spec.ts`: 9 passed (9)
- `packages/client/ui-conversation/tests/config.host.spec.ts`: 2 passed (2)
- `packages/client/ui-quote/` (6 test files): 45 passed (45)
- `packages/client/ui-workspace/` (15 test files): 512 passed (512)
- `packages/client/ui-theme/tests/hover-styles.client.spec.ts`: 2 passed (2)

**Total Test Count**: **33 test files, 852 tests passed, 0 failed**.

### 2.3 Golden Snapshot Delta Inspection (`apps/web/tests/expected/`)
All diffs under `apps/web/tests/expected/` were audited against base `dsh-v0.2.1-rc.2`:
- New localized snapshots added upstream for `de`, `es`, `fr`, `pt`, `ru`.
- Upstream schedule tool renames: `createSchedule` -> "创建自动化任务" / "Create automation task".
- Upstream ask-question turn inspection changes (checkpoint term definitions).
- No unintended regressions or unexpected snapshot mismatches.

---

## 3. Deployment & Live Transition Runbook

### Pre-Deployment Stash
- Stash command: `git stash push -u -m pre-0.2.2-2026-11-04`
- Existing patch backup: `~/.dsh/patches/archive-pre-0.2.2/`

### Live Application
1. Snapshot local kits: `bash ~/.dsh/bin/dsh-kit-snapshot.sh`
2. Stash live uncommitted changes: `git stash push -u -m pre-0.2.2-2026-11-04`
3. Checkout target tag: `git checkout dsh-v0.2.2-rc.1`
4. Archive old patches and copy v2 patches into `~/.dsh/patches/`
5. Run patch applicator: `bash ~/.dsh/bin/apply-dsh-patches.sh`

### User Restart Action
To activate the new DSH host, server, and client bundle:
```bash
bash ~/.dsh/bin/dsh-restart.sh
```
Check Web GUI on `http://127.0.0.1:3080`.
