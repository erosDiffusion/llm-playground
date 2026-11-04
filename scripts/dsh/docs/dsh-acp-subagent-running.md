# dsh-acp-subagent-running — external subagents showed an idle dot while working

**Kit:** `~/.dsh/patches/dsh-acp-subagent-running.patch` (89 lines, 4 files) · **upstream base:** `687f282e86`
(dsh-v0.2.1-rc.2 merge) · captured 2026-11-04.

## Symptom

A subagent started through a provider backend (`subagent_antigravity`, `subagent_copilot`,
`subagent_agy_opus`) shows a **grey `idle` dot** in the sidebar for its whole run, and the parent
session never shows "N subagents running". Children served in-process (the local model) behave
correctly. Not a colour choice: `ongoing` is already an animated spinner
(`packages/client/ui-primitives/lib/StateDot.module.css`), so grey-dot means "not running".

## Root cause

The GUI's running state has exactly two sources, both Agent-based:

- live: `packages/api/session-controller/src/index.ts:204` relays `agent/status` → `api-session/status`;
- baseline: `packages/client/ui-session/src/client/index.ts:503` seeds from `SessionSummary.running`.

A provider-backed child **owns a session but no in-process Agent**: `manager.ts` materializes it as
`{ kind: 'external', run, controller }` (the Agent path is the `kind: 'local'` branch, which calls
`agents.create/resume`). The subagent catalog projection carries only
`{ id, createdAt, mode, label }` (`packages/subagent/subagent/src/projection-types.ts`) — no state.
So neither source ever learns the child is busy, and `runningSubagentCount`
(`packages/client/ui-workspace/src/client/tree.ts:390`) counts only children whose status says running.

## Fix

Publish the fact once, at the one place that knows it, and relay it into the existing channel:

1. `packages/subagent/subagent/src/index.ts` — declare event
   `'subagent/run-status'({ sessionId, running })`.
2. `packages/subagent/subagent/src/manager.ts` — in the `kind === 'external'` branch, right after
   `assertChildIdAvailable`, emit `running: true`, and emit `false` from the run's **own** settlement
   (`run.result.then(ok, err)`), so pairing cannot be broken by any later failure.
3. `packages/api/session-controller/src/index.ts` — relay: `subagent/run-status` →
   `api-session/status`. The event is re-declared in that package's `remote-events.ts` (with
   `import type { SessionId }`) so the relay needs no new package dependency.

The client needs **no change**: `observeRunning` then clears `completionUnread` on start and sets it
when the run settles, so the row gets the spinner while working and the **green done dot** afterwards —
which is what the user expected ("green when finished"), reached through the existing design.

## Trap priced during this fix (do not re-litigate)

First version used `void run.result.finally(() => this.ctx.emit(...))`. It typechecked, but
`packages/subagent/subagent/tests/service.spec.ts` went from **49 passed / 0 errors** (baseline) to
**49 passed / 3 unhandled errors**: `.finally` leaves a chain whose rejection nobody handles, and the
spec deliberately fails `dispose()` and the transport during teardown, so an emit there became an
unhandled rejection. Fixed by wrapping the emit in `try/catch` (status is best-effort) and attaching
both settlements through `.then(ok, err)` plus a terminal `.catch`. Always diff the spec result against
the **baseline with the patch stashed** — a green "49 passed" line hid three new errors.

## Verification

- `pnpm exec tsc --noEmit -p packages/subagent/subagent/tsconfig.json` → 0
- `pnpm exec tsc --noEmit -p packages/api/session-controller/tsconfig.json` → 0
- `pnpm exec vitest run packages/subagent/subagent/tests/service.spec.ts` → **49 passed, 0 errors**
  (baseline without the patch: 49 passed, 0 errors — the patch adds no regression)
- Live check after applying: delegate to `subagent_antigravity`; the child row must show the spinner
  while it works, the parent row must read "1 subagent running", and the child must turn green at the end.

## Apply / replay

```bash
bash ~/.dsh/bin/apply-dsh-patches.sh      # idempotent, 3-way on drifted context, refuses on conflict
```

This is a **host-side** patch: it needs the host rebuild (the apply script does it) and a restart of
`~/.local/bin/dsh-web.sh`, which **drops the current GUI session** — do it as the last action of a
turn. Vault copy lives in llm-playground `scripts/dsh/` (this file in `scripts/dsh/docs/`).

## When to drop the kit

If upstream ever reports provider-backed children through `agent/status` (or adds state to the
subagent catalog projection), the relay becomes dead code: delete this patch and re-run the apply
script. Probe: `grep -rn "api-session/status" packages/api/session-controller/src/index.ts` and check
whether an `external` activation now creates an Agent.
