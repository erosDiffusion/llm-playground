# dsh-subagent-routing — kit #2 (spec, not yet implemented)

**Wanted behaviour (user, 2026-11-04):** a subagent shown in the GUI's subagent list must say which
**route** it took: copilot / antigravity / openrouter / local model, not just "a subagent".

## Why nothing can show it today

The route is known to the manager but is **never persisted anywhere the UI can read**:

- the sidebar nested rows are real sessions with `session.origin === 'subagent'`
  (`packages/client/ui-workspace/src/client/tree.ts:244`) and their text is `sessionTitle(s)`, derived
  from the first message — the subagent package never sets a title (`grep title` → no hits in
  `packages/subagent/subagent/src/`);
- the only subagent-side fact is the catalog projection entry
  (`packages/subagent/subagent/src/projection-types.ts:12-19`): `{ id, createdAt, mode, label }`;
- the sidebar activity tree item renders the **tool's** static description, proven by the golden
  `apps/web/tests/expected/sidebar-subagent-activity/owner-running.expected.md`:
  `treeitem "1 subagent running Delegate a background job. now"`.

## The change, with anchors

1. **Event + projection (persisted — the risky part).** `packages/subagent/subagent/src/catalog.ts`
   - `SubagentCatalogEvent` v2 variant (line 35): add `readonly provider?: string`.
   - zod: `externalCatalogSchema` (line ~70) is `oneShotCatalogSchema.extend(...)` and every member is
     **`.strict()`** → a new key is *rejected* unless the schema is extended in the same change.
     Use `provider: z.string().optional()` so already-persisted events still validate.
   - write site: line **167** (`mode: 'external',`) — pass the provider name that `MaterializeBase`
     already carries (`manager.ts`, `provider: string`), i.e. the ACP backend id (`gemini-copilot`,
     `gemini-antigravity`, …). Bump the variant to `version: 3` if you also add `model` — do **not**
     redefine version 2's meaning in place; readers key on the version.
   - `projection-types.ts:17` mirror the optional field on the entry.
2. **Model when the backend knows it.** The ACP config carries a model route
   (`packages/subagent/subagent-acp/src/index.ts` `Config`); surface it as `model?: string` on the same
   entry. Never guess from the label.
3. **Client render.** Add the route as a **secondary** label, never inside the accessible row title:
   - `packages/client/ui-workspace/src/client/tree.ts` (`sessionNode` ~397) read
     `list.projectionsBySession[parent].values.subagentCatalog` and expose `provider`/`model`;
   - render via the existing trailing/tag slot in `rows/Rows.tsx` (there is already a `trailingLabel`
     concept that replaces the update time).
   - **Snapshot risk:** `apps/web/tests/expected/sidebar-subagent-activity/` goldens capture aria text;
     a new visible node changes them. Keep the route in its own element and refresh goldens
     deliberately (`compareOrRefreshGolden`), with the diff reviewed line by line.

## Verification to run before generating the patch

```bash
pnpm exec tsc --noEmit -p packages/subagent/subagent/tsconfig.json
pnpm exec vitest run packages/subagent/subagent/tests/            # catalog + service specs
pnpm exec vitest run packages/client/ui-workspace/                # tree/row specs
# and compare every run against the baseline with BOTH kits stashed — see
# docs/dsh-acp-subagent-running.md for why (a green count hid 3 new errors there)
```

Then: `git diff -- <the explicit paths> > ~/.dsh/patches/dsh-subagent-routing.patch`,
`git apply -R --check`, register in `~/.dsh/bin/apply-dsh-patches.sh`'s patch dir (it globs
`*.patch`, alphabetical — this one must apply **after** `dsh-acp-subagent-running.patch` since both
touch `manager.ts` context), add the README row + this doc to the vault.

## Interim habit, zero risk (adopted 2026-11-04 while kit #2 is unimplemented)

The lead prefixes the delegation description with the route, so the route is readable wherever the
description is shown, and the row is never ambiguous about who is working:
`subagent_antigravity(description: "antigravity · port library.py")`, `subagent_copilot(description:
"copilot · audit auth")`. It does not replace the projection fix — it only makes the current UI honest.

## Why a spec instead of the code

The change edits a **persisted, `.strict()`-validated session event** plus aria goldens. That deserves
a fresh context with room for the schema migration and the snapshot review, not the tail of an already
long session.
