# scripts/strata/ — Strata brain box kit (local, untracked-in-repo artifacts)

The Strata checkout (`~/Apps/Strata`, upstream `github.com/Niko1221/Strata`) serves the agent brain on :8080
(config `strata-iq3_s.json`, launcher `START-262k.sh`). Upstream updates are applied by tag checkout — these files
are **untracked there**, so they survive checkouts but exist nowhere else. This is their durable copy
(user directive 2026-10-23: protocol + kit in the vault). Upgrade runbook lives in
[`../dsh-strata-upgrade-protocol.md`](../dsh-strata-upgrade-protocol.md) §B; flex API in
[`../strata-vram-flex.md`](../strata-vram-flex.md).

| file | what it does | archived from | date |
| --- | --- | --- | --- |
| `START-262k.sh` | the live launcher: `.venv/bin/python serve/server.py --engine strata --config strata-iq3_s.json --port 8080 --open`, refuses to start if :8080 is taken (262144 ctx, no rope scaling; siblings: `-conv`, `-network`, `-393k` variants live-only) | `~/Apps/Strata/START-262k.sh` (untracked) | 2026-10-23 |
| `warm-build.py` | byte-identical copy of `warm-build-2026-10-13.py` — warms `build/` + `build-vision/` with setup.py's EXACT `build_engine` defs WITHOUT touching `engine/` (locked by the running server), so the swap stop→copy is seconds. Imports setup.py as a module (`main` is `__main__`-guarded), reads `engine/BUILD.json` for archs. Verified working unchanged on v0.2.2 | `~/Apps/Strata/warm-build-2026-10-13.py` (untracked) | 2026-10-23 |
| `swap-strata.sh` | **generalized** engine swap (was the dated `swap-2026-10-21.sh`): SIGINT `serve/server.py` → wait for :8080 free → `sh setup.sh --update` (no-op build + engine copy + stamp; old binaries → `engine/.previous`) → `START_SCRIPT` detached → poll `/health` → log. RUN DETACHED; drops the brain ~90 s–3 min, needs user OK. Env: `START_SCRIPT`, `PORT`, `STRATA_HOME`. Live copy: `~/.dsh/bin/swap-strata.sh` | generalized 2026-10-23 from the applied 2026-10-21 swap (log: brain down 26 s, /health green, 182 tok/s) | 2026-10-23 |
| `strata-upgrade-check.sh` | read-only preflight: lists remote tags + fetches only the target tag ref (`git fetch --tags` breaks after the 2026-10 history rewrite — "would clobber existing tag"), extracts the LIVE engine's launch flags from `/proc/<pid>/cmdline` (fallback: config `args`), greps each in the new tag's source, verifies `serve/server.py` + `setup.py` + `setup.sh` + config keys. No risk to the running brain; self-tested 2026-10-23 (16 live flags vs v0.2.2 and v0.1.39: 0 missing). Live copy: `~/.dsh/bin/strata-upgrade-check.sh` | authored 2026-10-23 (automates the manual 14-flag check of 2026-10-21) | 2026-10-23 |
| `bench-strata.py` | deterministic before/after performance probe: 3 greedy 256-token /v1/chat/completions vs :8080 with per-run nonces, medians of `timings.predicted_per_second` / `prompt_per_second` (llama.cpp names, same fields Strata Control's benchmark reads), JSON out + slots/BUILD.json context. Pure HTTP, safe while the brain is live. Live copy: `~/.dsh/bin/bench-strata.py`, results in `bench-results/` | authored 2026-10-31 (user order: benchmark before/after every Strata upgrade) | 2026-10-31 |
| `UPDATE-2026-10-13.md`, `UPDATE-2026-10-21.md`, `UPDATE-2026-10-27.md` | dated handoff sheets from the three applied upgrades (state, compatibility checks, apply/rollback, gotchas) — kept verbatim as the archaeology trail | `~/Apps/Strata/UPDATE-*.md` (untracked) | 2026-10-27 |

**Applied 2026-10-31:** v0.2.7 → **v0.2.8**, engine 0.1.52 → **0.1.54**.
Preflight clean (18 flags 0 missing, 0 config keys missing); warm-build unchanged (CUDA ON confirmed, ggml
commit = tag tip); detached swap: stop→`setup.sh --update`→launcher OK, engine back ~45 s. Bench (new protocol
step): decode median 200.5 → 199.9 tok/s (best run 201.7 → 217.1), prefill ~391 → ~377 — flat, no regression.
Engine 0.1.54 carries the #4474 expert-cache accounting fix: the auto cache now leaves ~256 MiB for the CUDA
allocations that land after sizing — full cache 9,574 slots ≈ 18.6 GB (with the live `--slots 2` config it was
9,657 pre-upgrade, so the fix re-priced only ~83 slots ≈ 160 MiB; 10,816 is the flag-free number). The reserve
is now honest — flex probe at `reserve_mib:null` reports 2,474 MiB free (≥ 2,048 requested; pre-upgrade the same
config left nvidia-smi at 1,481 MiB free, i.e. ~570 MiB under reserve, engine 0.1.52 + #4474 absence).
Flex down/up round-trip verified (515 slots,
19,369 MiB free at reserve 22016). Lesson in runbook §B.5: do NOT chain post-swap steps onto the detached swap —
the setsid chain was reaped mid-poll with the session's tool scope; post-checks run from the resumed chat.
Rollback armed: `engine/.previous` holds 0.1.52.

**Applied 2026-10-27 (first full run through this protocol):** v0.2.2 → **v0.2.7**, engine 0.1.47 → **0.1.52**.
Preflight 18 flags 0 missing; `warm-build.py` worked UNCHANGED on 0.2.7 too (275 targets, 3m27s, brain never
stopped); detached swap: `swap OK` logged, `/health` green, flex + vision + tool-calling all verified after
restarting the chat. Note: a parallel session's 2026-10-23 config change (`--slots 2 --batch-mtp`) is now in the
live launch line — it shrinks the full expert cache 10,816→9,657 slots, and decode measured 147 tok/s under it
vs 182 pre-`--slots` on 0.1.47 (not directly comparable — re-measure with the flags off before blaming the
engine). Rollback still armed: `engine/.previous` holds 0.1.47.

Not archived (deliberately): the tarball `~/backups/strata-update-2026-10-21/` holds a pre-upgrade snapshot of ALL
untracked Strata files (incl. `-conv`/`-393k`/`-network` launchers and the never-installed `/v1/embeddings`
experiment patch `0001-serve-EMBD-*.patch`, which CONFLICTS with 0.2.x — rework by hand if ever wanted).
`ROLLBACK-2026-10-13.sh` is superseded (goes back to the pre-history-rewrite state; history was rewritten upstream
2026-10-06/10-13 — the cleanup recipe lives in upstream `update.sh` + decision log 2026-10-13).

Standing cautions:
- Never stop/restart the brain ad-hoc (user-managed process); the swap script with explicit user OK is the ONLY
  sanctioned stop path. Flexing (`/v1/vram`) never touches the process.
- Packs, models, `strata-iq3_s.json` are never touched by tag checkouts — never re-download on upgrade.
- Rollback always: `python3 setup.py --rollback-engine` (engine ⇄ `engine/.previous`) + `git checkout <old-tag>` +
  launcher (`START-262k.sh` refuses if :8080 still busy — stop the old one first).
