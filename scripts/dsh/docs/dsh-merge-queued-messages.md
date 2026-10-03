# Merge queued messages (auto-merge on submit)

Local DSH patch: **`~/.dsh/patches/dsh-merge-queued-messages.patch`**
Applies on top of checkout HEAD **`0d1f50007f`** (v0.1.2-alpha.4).
Survives platform updates via the standing local-patch protocol
(`~/.dsh/bin/apply-dsh-patches.sh`).

## What it does

When the addressed agent is busy and you send another **plain text** message
(the delivery mode resolves to `queue` — i.e. plain Enter while running, or the
Send button), the new message is **merged into the newest still-pending queued
row** instead of becoming a separate turn. A visible switch sits next to the
Send button to toggle the behavior; it is **on by default**.

```
[queued] "first"   [queued] "second"        user types "third" + Enter
                                        └─► [queued] "first"   [queued] "second\n\nthird"
```

Only the **last** queued row grows. Earlier rows are never touched (the merge is
non-destructive to anything already queued).

## Why it is safe / the invariants

The merge reuses the **existing** `session.updateQueue(itemId, {kind:'edit'})`
wire verb — no Host, wire, or typert changes. That keeps the whole feature
client-side (a page refresh is enough to enable it; no process restart for the
merge itself). The Host's `edit` action is text-only by contract, which drives
every guard:

- **Only when delivery mode is `queue`** (not `steer`).
- **Only for a text-only send** (no draft attachments).
- **Only when the target row is text-only** (`QueuedMessage.text !== null`);
  a row carrying an image/file cannot be represented by a text-only edit.
- **Only when the merge switch is on.**
- **No `beginSubmission` echo on the merge path.** The merged text lands on the
  existing row's identity; registering a new pending-submission echo would stick
  as "Sending…" forever because the row keeps its original `rpcId`.
- **Subagent-addressed sessions are skipped** (they take the dedicated
  continuation branch earlier in `sendSession`).

Race handling: if the target row is claimed between reading it and the edit
reaching the Host, the Host returns `session/queue-item-not-found`; the client
then **falls back to the ordinary queue path** (the message is not dropped). Any
other `updateQueue` error **throws**, so the composer restores the draft and
surfaces an error notice (same failure contract as a normal send).

## The switch

- Composer-bar seat, right of the Context meter, left of Send/Stop.
- 28px round chip (same seat as the attach control), transparent at rest,
  business-blue (`--dsw-alias-state-business-primary`) when on.
- `aria-pressed` reflects state; tooltip = `input.mergePending`
  ("Merge queued messages" / "合并排队消息"); disabled while the bar is locked.
- Absent in the no-session surface (the preference is per-addressed-session).

## Settings & persistence

New durable field **`mergePending: boolean`** (default `true`) in the shared
`ui-conversation` settings section.

- **Shared schema** (`submission-settings.ts`) is registered by the Host entry
  (`src/index.ts` → `ctx.inject(['settings'])` → `settings.register`), so the
  Host validates/stores it and the browser `SettingsScope` reads it back.
- **Graceful degradation across a version gap:** the currently-running dsh
  process registers the section from the schema that was loaded at boot. Until
  the process restarts with the rebuilt host lib, the old schema **strips**
  `mergePending` on the resolved read (and stores the raw value). The client
  `adopt()` guards with `typeof section.mergePending === 'boolean'`, so a
  stripped field never clobbers the live in-memory default. The switch keeps
  working in memory immediately; the value is picked up durably at the next
  dsh boot.
- **Build note:** for `ui-conversation`, the Node/host half
  (`lib/index.js`) is emitted during the **client** build face
  (`clientBundle` host phase is skipped), so `build:lib:client` regenerates the
  host registration artifact. `build:lib:host` is still run in the patch
  script so future host-side (settings/service) patches are covered uniformly.

## Files changed (16)

Source (9):
- `src/submission-settings.ts` — `MERGE_PENDING_FIELD`, `DEFAULT_MERGE_PENDING`,
  `mergePending` on `ConversationSettings` + schema.
- `src/index.ts` — re-exports the new constants.
- `src/client/input/submission-policy.ts` — `mergePending` store (default on),
  `setMergePending()`, `adopt()` handling for the field (with the old-host guard).
- `src/client/contract/slots.ts` — `ComposerBarInjected.setMergePending` +
  `hooks.mergePending: ObservableSnapshot<boolean>`.
- `src/client/service.ts` — merge gate in `sendSession` + `mergeIntoQueue()`.
- `src/client/skeleton/InputBar.tsx` — the toggle (destructure, state, render).
- `src/client/skeleton/InputBar.module.css` — `.merge` / `.mergeOn` / hover.
- `src/client/locales.ts` — `input.mergePending` (en + zh).
- `src/client/apply.ts` — wires `setMergePending` + `hooks.mergePending` into
  both inject branches and the `ConversationController` config.

Tests (7):
- `tests/submission-policy.client.spec.ts` — default/toggle/write-through/adopt
  + old-host-strip cases.
- `tests/service-orchestration.client.spec.ts` — merge into newest row, disabled
  skip, attachment/non-text-row skip, steering/context-row skip, claimed-row
  fallback, genuine-failure rejection.
- `tests/input-bar.client.spec.tsx` — toggle render/default, inherited off,
  locked/disabled.
- `tests/host.client.spec.ts` — section now resolves `{busyEnter, mergePending}`;
  `mergePending` write + invalid-value rejection.
- `tests/input-matrix.client.spec.tsx`, `tests/input-scenarios.client.spec.tsx`,
  `tests/skeleton.client.spec.tsx` — fixtures supply the new required
  `setMergePending` + `useMergePending` props.

## Verification performed

- `tsc -b tsconfig.client.json` and `tsc -b tsconfig.host.json` — clean.
- Full `packages/client/ui-conversation` vitest suite — **430/430 pass**.
- `build:lib:host`, `build:lib:client`, `build:web` — success;
  `lib/index.js` (host half) and `lib/client.js` (browser half) both contain
  `mergePending`.

## Applying / persisting

```
bash ~/.dsh/bin/apply-dsh-patches.sh      # after any git update flow
```
Idempotent: detects the patch is already applied (`git apply --check --reverse`)
and skips. On drift it attempts `--3way`. After any patch applies it rebuilds
host + client + web.

## Capability ideas (future)

- **Merge scope option:** today merges into the *newest* queued row. A setting
  could instead (a) merge into *all* pending rows, or (b) merge only when the
  newest row is from the same sender/turn.
- **Merge delimiter:** fixed `\n\n`; could become configurable (blank line,
  `\n`, `— `, a timestamp).
- **Merge cap:** bound the merged row's length (e.g. stop merging past N chars
  or M turns) to keep one queued message from ballooning.
- **Per-session memory:** the preference is global; could be remembered per
  session or per workspace.
- **Steer-then-merge:** allow a merge to also *steer* the running turn when the
  queued rows are about to be consumed.
- **UI affordance on the queued row:** show a subtle "merged ×N" badge on the
  dock row when it has absorbed more than one send, with an expand to see parts.
- **Undo/inspect:** since a merge rewrites a pending row, offer a quick
  "split back out" for the last merge before the row is sent.
