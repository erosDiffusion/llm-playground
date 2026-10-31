# DSH + Strata upgrade protocol (fast, deterministic, zero additions lost)

Provenance: consolidated 2026-10-23 from the live upgrades of 2026-10-03 (0.1.6→alpha.1), 2026-10-12 (alpha.1→alpha.2),
2026-10-13 + 2026-10-21 (Strata 0.1.39→0.1.43.1 prep → v0.2.2/engine 0.1.47), 2026-10-21 (DSH alpha.2→rc.2),
the `dsh-local-patch-protocol` skill, and decision-log entries 2026-10-12 / -13 / -21. This file is the **single
runbook**; the skill keeps only the patch-kit detail, the decision log keeps only dated outcomes.

Known-good baseline when this was written (re-probe with the commands in §0, never trust the numbers):
- DSH checkout `~/Apps/deepseek-harness` @ tag `dsh-v0.2.1-rc.2` (687f282e86), working tree = tag + 4 local patches
  applied UNCOMMITTED. Kit: `~/.dsh/patches/` (merge-queued v3, quote v3, mermaid v2, video-inline) +
  `~/.dsh/bin/apply-dsh-patches.sh` (live) = vault [`dsh/`](dsh/README.md).
- Strata checkout `~/Apps/Strata` detached @ tag `v0.2.2` (011c9e60), engine `engine/BUILD.json` version 0.1.47
  RUNNING on :8080 (this agent's brain). Old binaries kept in `engine/.previous`.
- NInfer kit: vault [`ninfer/`](ninfer/README.md) — same patch-kit pattern, covered there, not repeated here.

## Golden rules (each cost a broken session to learn)

1. **The DSH host runs FROM SOURCE** (`~/.local/bin/dsh-web.sh` → `node --import tsx/esm apps/cli/src/bin.ts
   --profile web-lite`). After any pull/checkout + patch apply the RUNNING host is stale vs the tree and every NEW
   tool subprocess (bash, grep, subagents) dies with "subprocess scope exited before its bootstrap consumed the
   launch request". Restart `dsh-web.sh` IMMEDIATELY after the apply script — nothing else recovers it (2026-10-12).
   The restart drops the running GUI/agent session → it is the LAST action of the turn; resume the session in the
   GUI (http://127.0.0.1:3080) afterwards.
2. **Local additions are never committed into the checkout.** DSH extras live as standalone git patches in
   `~/.dsh/patches/`; Strata extras live as UNTRACKED files (launchers, warm-build, handoff sheets) which checkouts
   never touch. Upgrade = move the checkout, re-apply kit, restart. There is nothing to "carry" by hand.
3. **Before moving the DSH checkout, save the live tree** with `git stash push -m "pre-<newtag>-<date>"` — the tree
   holds the applied patches; a bare `checkout`/`reset` would destroy any hand drift not yet captured in a patch.
4. **Strata's running engine cannot be replaced in place** (`setup.py --update` refuses, ETXTBSY, and silently
   skips the engine step only). Correct order: checkout new tag → **warm-build while running** → user OK → detached
   swap script (SIGINT server → finish update → restart → health-poll). Brain down ≈90 s–3 min. NEVER park/resume
   scripts; they're dead (studio era).
5. **Tests: `pnpm exec vitest run packages/client` — NEVER `npx vitest`** (npm_execpath breaks the
   documentpreview license-pack spec).
6. Engine/tag updates never touch Strata packs, models, or `strata-iq3_s.json` (verified 2026-10-21); never
   re-download anything during an upgrade. The 190k-token prompt cache even survives the restart.
7. Two session-drops exist (DSH GUI restart, Strata brain swap) — batch them: do all quiet prep first, then drop
   once each, in one idle window. Ask the user before the Strata swap (it kills the chat mid-turn).

## 0. Snapshot both systems (read-only, ~10 s)

```bash
# DSH state
cd ~/Apps/deepseek-harness && git describe --tags && git log -1 --oneline && git status --porcelain | head
git stash list | head -3
# Strata state (engine stamp = what actually runs)
cd ~/Apps/Strata && git describe --tags && cat engine/BUILD.json | head -4
pgrep -af 'engine/strata --serve' | head -2
```

Record the outputs — they are the rollback anchor (current tag + stash name to create).

## A. DSH upgrade (host restart = one session drop, ~15 min wall)

1. **Fetch + pick target:** `git fetch --tags && git tag --sort=-creatordate | head -5`.
2. **Save live state:** `git stash push -m "pre-<newtag>-<YYYY-MM-DD>"`. Then the tree must be clean
   (`git status --porcelain` empty). If the tree had drift beyond the 4 patches, FIRST regenerate the affected
   patch from it (`git diff --cached -- <paths> > ~/.dsh/patches/<name>.patch`, verify `git apply -R --check`)
   — never stash-and-forget drift.
3. **Dry-run in a scratch worktree** (never discover a conflict on the live tree — 2026-10-12 lesson):
   ```bash
   git worktree add /tmp/dsh-try <newtag>
   cd /tmp/dsh-try
   for p in ~/.dsh/patches/*.patch; do git apply --check "$p" || echo "DRIFT: $p"; done
   cd .. && git worktree remove /tmp/dsh-try
   ```
   All silent → proceed. Any DRIFT → resolve NOW (see step 5 playbook) against the new tag before touching the live tree.
4. **Move live tree + re-apply + build:**
   ```bash
   git checkout <newtag>
   bash ~/.dsh/bin/apply-dsh-patches.sh        # idempotent; pnpm install + host/client/web builds; refuses to
                                               # rebuild on CONFLICT
   ```
5. **Conflict playbook** (patch context drifted upstream): `git apply --3way <patch>` (the script already tried),
   open the conflicted file, re-splice by hand using the drift map in [`dsh/README.md`](dsh/README.md) — known hot
   spots: merge-queued block in `ui-conversation/src/client/apply.ts` (upstream removed the old anchor in rc.2),
   quote patch's `clientBundle(import.meta.dirname)` signature + ui-theme lint fixtures, mermaid is
   order-independent. Then REGENERATE the patch from the resolved tree:
   `git diff --cached -- <paths> > ~/.dsh/patches/<name>.patch` (stage first; verify `git apply -R --check`),
   bump the version note in [`dsh/README.md`](dsh/README.md), and refresh the vault copies through the worktree flow.
6. **Test:** `pnpm exec vitest run packages/client` (expect ≈10.6k green at rc.2). Broken spec vs broken patch:
   bisect by `git stash push` of the patch files — do not skip tests.
7. **Restart the host (LAST action of the turn):** stop the `dsh-web.sh` terminal (Ctrl+C / kill the bash pid — the
   node child exits with it), relaunch `~/.local/bin/dsh-web.sh &` detached, then resume the chat session in the GUI
   and refresh the browser page once (client bundle is static; no web HMR).
8. **Post-upgrade probes** (bundle rows are untouched by the checkout but must re-resolve):
   ```bash
   pnpm run dsh --profile web-lite --dump-config | grep -E 'dsh-movie-studio|dsh-strata-flex'
   curl -s http://127.0.0.1:3080/api/movie-studio/state | head -c 200
   curl -s http://127.0.0.1:3080/api/strata-flex/state  | head -c 200   # 200/JSON = mounted; 'unauthorized' = skipped
   ```
   A skipped bundle → nudge HMR reconcile with a comment line in `~/.dsh/profiles/web-lite/cordis.patch.yml`
   (details + restore checklist: vault [`../projects/dsh-customizations/bundles/dsh-strata-flex/`](../projects/dsh-customizations/bundles/dsh-strata-flex/)).

**DSH rollback (template — write it BEFORE moving the tree, one per upgrade):**
```bash
git reset --hard <old-tag> && git clean -fd && git stash pop   # stash = the pre-<newtag> snapshot
# or, if no stash: git checkout <old-tag> && bash ~/.dsh/bin/apply-dsh-patches.sh  (old patch versions in
# ~/.dsh/patches/archive/ = archive/<name>.pre-<newtag>.patch)
# then restart dsh-web.sh. Reference implementation: ~/.dsh/bin/rollback-dsh-to-alpha2.sh
```

## B. Strata upgrade (engine swap = one brain drop ~90 s–3 min, needs user OK)

Quiet part first — it can run any time while the brain is live and costs nothing if aborted:

1. **Preflight (read-only):** `bash ~/.dsh/bin/strata-upgrade-check.sh` — lists remote tags and fetches ONLY the
   target tag ref (do NOT `git fetch --tags`: after the 2026-10 upstream history rewrite it exits 1 on old tags,
   "would clobber existing tag"), extracts the live engine's actual launch flags from `/proc/<pid>/cmdline`
   (fallback: the config's `args` array), greps each flag in the newest tag's source, and checks
   `serve/server.py` + `setup.py` + `setup.sh` + config-key presence. Anything flagged MISSING = review that flag
   by hand before proceeding. (Manual version of these checks on 2026-10-21: 14 flags, all present in 0.2.2.)
2. **Benchmark BEFORE (baseline, ~1 min):** `python3 ~/.dsh/bin/bench-strata.py --label before-<oldtag> --runs 3
   --out ~/.dsh/bench-results/<date>-<oldtag>-before.json` — greedy 256-token /v1/chat/completions against :8080,
   per-run timings read from the reply's `timings` block (llama.cpp names: `predicted_per_second`,
   `prompt_per_second` — same fields Strata Control's native benchmark uses), medians reported, JSON saved.
   (Added 2026-10-31 on user order; baseline v0.2.7/engine 0.1.52: decode ~200 tok/s, prefill ~390; a first run
   right after idle ~140 = cold expert cache, ignore it, the median is the number.)
3. **Move code WITHOUT touching the running engine:** `cd ~/Apps/Strata && git checkout <newtag>`.
   Untracked local files (START-*.sh, warm-build, configs, `engine/`, packs) survive every checkout — they are
   untracked; verify with `git status --porcelain` after.
4. **Warm-build while running:** `cd ~/Apps/Strata && .venv/bin/python warm-build-2026-10-13.py` — calls setup.py's
   own cmake_build with build_engine's exact defs into `build/` + `build-vision/`, never touches `engine/`
   (locked by the live server). Proven unchanged on 0.2.2; if setup.py hooks moved (function renamed), diff against
   vault copy [`strata/warm-build.py`](strata/warm-build.py) and update. Cmake gotcha (2026-10-13): if the CUDA
   compiler path changed, cmake can silently reconfigure with CUDA OFF → `rm -rf build/ build-vision/` and re-run.
5. **Ask the user for the brain-drop window.** Then run the swap DETACHED (this session dies with it):
   `setsid bash ~/.dsh/bin/swap-strata.sh >/dev/null 2>&1 &` — env `START_SCRIPT` (default `START-262k.sh`),
   `PORT` (8080). It SIGINTs `serve/server.py`, waits for :8080 to free, runs `sh setup.sh --update` (now a no-op
   build + seconds-long engine copy; stamps BUILD.json; old binaries → `engine/.previous`), starts the launcher
   detached, polls `/health` until `"loaded": true`, logs to `swap-<date>.log` with the rollback line on timeout.
   Do NOT chain follow-ups (bench, flex probe) onto the detached swap: 2026-10-31 the setsid chain was reaped
   mid-poll together with the dead session's tool scope (the swap itself had finished stopping/building/launching,
   so the engine came back anyway) — run every post-swap check from the RESUMED session instead.
6. **Resume the chat session in the GUI** once `/health` is green (the GUI/DSH process itself never dies).
7. **Post-swap verify + benchmark:** `cat ~/Apps/Strata/engine/BUILD.json` (new version) → re-run the bench
   `--label after-<newtag> --out ~/.dsh/bench-results/<date>-<newtag>-after.json`, diff medians vs BEFORE;
   judge decode tok/s mainly (expect ~180–220 at full cache; a first post-boot run lower = expert cache not
   warmed, fine). A cache-accounting fix in engine 0.1.54 (#4474) re-priced late CUDA allocations, so full
   auto-cache sizing moved to 9,574 slots ≈ 18.6 GB and the reserve is now honest (probe: 2,048 reserve →
   2,474 MiB free, 2026-10-31; pre-fix the card ran ~240 MiB UNDER the requested reserve) — a ~1–4 % prefill
   drift from the smaller cache is expected, not a regression.
   → flex API still alive:
   `curl -sX POST 127.0.0.1:8080/v1/vram -d '{"reserve_mib":null}'` returns the state probe (see
   [`strata-vram-flex.md`](strata-vram-flex.md)). "Re-runs do not tune again" (0.2.x): second launch ≈13 s, not 520 s.

**Strata rollback (one line, seconds):**
```bash
cd ~/Apps/Strata && python3 setup.py --rollback-engine   # engine/ <-> engine/.previous
git checkout <old-tag> && sh START-262k.sh               # launcher refuses if :8080 still busy
```
Second copy of older binaries: `engine/pre-update-*/` (per-swap stamps). Reference handoff sheets (local, kept in
the repo untracked + archived in vault [`strata/`](strata/README.md)): `UPDATE-2026-10-13.md`, `UPDATE-2026-10-21.md`.

## C. Close-out (always, 5 min)

1. Decision log (`~/.dsh/memory/decisions.md`): one dated line — old→new versions, patch re-merges (versions bumped),
   test count, rollback anchor (stash name / old tag).
2. Vault refresh (this repo, worktree flow): updated patches + README drift map if any patch changed; new
   `swap-<date>.log` outcome noted in [`strata/README.md`](strata/README.md) if something drifted.
3. Re-verify profile bundles + flex footer buttons (probes in §A.8).
4. Dated rollback scripts: keep exactly ONE (the latest); archive older into `~/.dsh/patches/archive/`.

## Time budget (proven 2026-10-21)

| step | cost |
|---|---|
| §0 + §B.1 preflight | ~1 min, zero risk |
| §A.3 dry-run (3 patches) | ~1 min |
| §A.4 apply + builds (no conflict) | ~5–10 min |
| §A.6 client tests | ~3–5 min |
| §B.2 BEFORE bench | ~1 min, zero risk |
| §B.3–4 warm build (cached) | 1–5 min (65 s full recompile seen when CUDA defs changed) |
| §B.5 brain drop | ~90 s (timeout 300 s then rollback; engine back ~45 s 2026-10-31) |
| §B.7 AFTER bench + flex probe | ~1.5 min |
| worst case (patch conflicts) | +30–60 min hand re-merge, live tree untouched |
