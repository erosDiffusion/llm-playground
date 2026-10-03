# dsh-quote-selection — quote surface (local patch)

Added 2026-09-18 against checkout HEAD `0d1f50007f` (v0.1.2-alpha.4);
paragraph box + click fix + hover grace the same day.
Patch file: `~/.dsh/patches/dsh-quote-selection.patch` (27 files: 22 new
`packages/client/ui-quote/` sources + `ui-chat/MessageIconActions.module.css`
grace change + web-app composition row + web-app `package.json` dep +
`tsconfig.client.json` reference + `pnpm-lock.yaml`).

## What it is

Three affordances, one shared per-Session dialog:

1. **Per-paragraph quote box** (the primary UX): hovering any paragraph
   (`p/li/blockquote/pre/h1..h6`) inside an assistant step shows a 28px
   quote glyph in the left margin of that paragraph. Clicking it opens the
   dialog with **that paragraph's rendered text** quoted. It works on the
   step that is *still rendering or thinking* — the tracker reads the live
   DOM (no finalized blocks required; `turn`+`time` are recorded before the
   step closes) — which is the in-context steering case. The box lingers
   350ms after the pointer leaves the paragraph so it can be reached across
   the left margin; scrolling/resize dismisses immediately.
2. **Strip quote icon**: the hover-revealed icon in the assistant action
   strip quotes the **whole message** (all text blocks joined). Clicking it
   resolves the owning step from the seat owner's `messageId` by scanning
   `ChatSnapshot.nodes` (the strip renders inside the *turn-tail* node,
   whose payload is not the step data — the original click bug).
3. **The dialog** (`conversation.input.overlay` seat, `Modal`):
   read-only preview of the quoted text with the self-describing header
   `assistant · turn N · step M · <ISO+offset> [· msg <id>]` (the msg id is
   omitted for mid-stream quotes that predate finalization) + comment
   textarea + footer:
   - **Send** — `inputActions.setDraft(quote + comment + existing draft)`
     then `submit()`. Steers while the session is busy via the queue.
   - **To composer** — stages the same composition without submitting.

Reasoning blocks stay out by design (visible text as rendered is what gets
quoted). 4000-char cap with a `truncated` flag.

## Hover reachability (user-reported, fixed)

Both affordances started life as "vanish as soon as the pointer leaves":

- Strip: the reveal row faded out in 80ms. The `MessageIconActions.module.css`
  change splits the transitions — hidden state owns a **400ms fade-out**
  (grace to reach the icons; opacity never disables pointer-events, so a
  pointer arriving during the grace re-triggers the **80ms fade-in** owned
  by the `:hover/:focus-within` state).
- Paragraph box: the 34px margin crossing between text and box leaves the
  paragraph (no hover target) — the tracker schedules a 350ms hide that the
  box itself cancels (`[data-dsw-quote-box]` hit-test) and that a new
  paragraph preempts.

## Decisions locked by the user

- Per-paragraph left-margin box is the wanted UX ("not for the whole turn
  response"); the strip icon is kept as the whole-message quote.
- The affordance must exist **while output renders and while thinking** —
  steering within context.
- Reasoning stays as is; no right-click range quote (parked).

## Architecture (zero wire/host changes)

The quote rides the existing prompt wire as formatted text
(`PromptContentPart {type:'text'}`). All client-side over published
contracts:

| Piece | Source |
|---|---|
| Entry 1 (strip icon) | `conversation.chat.assistant-actions` (ui-chat; session scope, owner `messageId`) |
| Entry 2 (dialog) | `conversation.input.overlay` (ui-conversation; session scope, order 3) |
| Entry 3 (paragraph tracker) | `conversation.input.overlay` (session scope, order 4) — one tracker per Session, portaled to `document.body`, follows the document-level `mousemove` |
| Standard kit | `SessionStandardProps` auto-merged: `useConversation`, `useInput`, `inputActions` |
| Step data | `useConversation(s => s.views.get('chat'))` → `ChatSnapshot`; strip: `nodes.values()` scan for `finalNode.messageId === owner.messageId`; tracker: seat wrapper `data-chat-anchor-key` → `nodes.get(key).data` (`AssistantChatData`), loose guard (`turn`+`time` numbers only) |
| Paragraph hit-test | `mousemove` → `closest('p,li,blockquote,pre,h1..h6')` → `closest('[data-chat-anchor-key][data-chat-flow-kind="assistant-step"]')` |
| Composer | `InputActions.setDraft(text)` + `InputActions.submit()` |
| Dialog shell | `Modal` (ui-primitives) — body-portaled, `role=dialog` only while open |
| Copy | `quote` locale namespace (en + zh, key parity via `satisfies`) |

Per-Session `QuoteSurface` (one `createSnapshotStore<QuoteDialogState>`)
backs all three entries of one session; two sessions are isolated; surfaces
are retired with the plugin fiber.

## Files

```
packages/client/ui-quote/
  package.json            dsh.client.inject [locale, ui-conversation, ui-renderer]; platform web
  tsconfig.json           references: cordis, core/session, locale, store, ui-chat,
                          ui-conversation, ui-primitives, ui-renderer, ui-slots
  tsdown.config.ts        clientBundle('@deepseek-ai/dsh-client-ui-quote', ['lib/types/index.js'])
  src/index.ts            host stub (empty apply — pure UI plugin)
  src/css-modules.d.ts
  src/client/quote.ts     pure logic: QuoteTarget, quoteTextOf, buildTarget (cap),
                          formatQuoteTime (local ISO+offset, second precision),
                          buildQuoteBlock, composeDraft
  src/client/surface.ts   QuoteSurface + QuoteDialogState + QUOTE_CLOSED
  src/client/slots.ts     QuoteActionProps / QuoteDialogProps / ParagraphTrackerProps
  src/client/locales.ts   en/zh dictionaries + LocaleNamespaceMap merge
  src/client/actions.tsx  strip icon entry: QuoteGlyph, quotableData, resolveStepById,
                          QuoteActions (owner messageId → node scan; no busy gate —
                          quoting while busy is the steering case)
  src/client/paragraph.tsx  ParagraphQuoteTracker: stepAnchorsOf, capParagraphText,
                          document-level mousemove tracker + 350ms grace + portaled box
  src/client/dialog.tsx   QuoteDialog modal entry
  src/client/{actions,dialog,paragraph}.module.css
  tests/                  45 specs: pure logic, surface, actions, dialog, paragraph
                          tracker (grace via fake timers), browser plugin (3 entries)

packages/client/ui-chat/src/client/chat/MessageIconActions.module.css
                          reveal grace: hidden state 400ms fade-out, hover state
                          80ms fade-in (affects all message strips — intentional)
```

Composition wiring (in the patch):

- `packages/bundle/web-app/cordis.patch.yml`: `- id: ui-quote /
  name: '@deepseek-ai/dsh-client-ui-quote'` after `ui-message-feedback`.
- `packages/bundle/web-app/package.json`: `+ "@deepseek-ai/dsh-client-ui-quote": "workspace:^"`.
- `tsconfig.client.json`: `+ { "path": "./packages/client/ui-quote" }`.
- `~/.dsh/profiles/web/cordis.patch.yml`: same row at the profile layer for
  the live process (`patchReload: live`); dedupes by id after restarts.
- `~/.dsh/bin/apply-dsh-patches.sh`: runs `pnpm install` before the rebuilds
  (new workspace package must be linked).

## Live reload (verified)

No process restart needed: the `client-hmr` node half stat-polls every
graph row's `lib/client.js` (500ms); a changed mtime/size triggers
`clientModules.rebuilt(id)` → new rev → recomposed boot graph → SSE frame →
the browser HMR half swaps the entry fiber in place (invalidate → prefetch
→ teardown → re-materialize). Verified: after `pnpm build:lib:client`, the
live boot graph's ui-quote rev changed without a restart.

## Build & verify (done)

- `tsc -b tsconfig.client.json` — clean.
- `vitest run packages/client/ui-quote/tests` — 45/45.
- `pnpm build:lib:client && pnpm build:web` — clean;
  `packages/client/ui-quote/lib/client.js` (~27 kB) + web dist rebuilt.
- CDP live probes (headless Chrome on :9333, probe scripts
  `/tmp/cdp-probe*.mjs`): paragraph box appears on `<p>` hover; lingers
  across the margin during the grace; clicking opens the dialog with the
  paragraph text + `turn/step/ISO/msg` header; strip icon (on a finalized
  turn in a fresh session) stays opaque along the approach path and its
  click opens the dialog with the whole-message quote.

## Pitfalls hit

- **The strip click bug**: the action strip renders inside the *turn-tail*
  node, whose payload is not the assistant step data. Resolving the step
  via the seat wrapper's `data-chat-anchor-key` (the turn-tail's own key)
  yields no `blocks` → silent no-op. Fix: the seat declares
  `owner: { messageId }` — resolve by scanning `ChatSnapshot.nodes.values()`
  for the step whose `finalNode.messageId` matches.
- **Turn-tails only exist on finalized turns** (`turn/end`); the live turn
  (and pre-compaction history, folded into the compaction node) has none —
  so the strip is invisible while a turn is open. The paragraph box is the
  streaming-path affordance.
- **Virtualized chat list**: programmatic `scrollTop` on the wrong ancestor
  scrolls nothing; the real scroller is the innermost
  `scrollHeight>clientHeight` + `overflowY:auto|scroll` ancestor
  (`NcgJLW_scrollBody` at the time).
- `AssistantChatData`/`ChatSnapshot` export from `.../ui-chat/client`, not
  ui-conversation (ui-conversation re-exports only record types).
- The `ConversationViewSnapshotMap['chat']` merge (and
  `LocaleNamespaceMap`) are declaration merges — type-only import of the
  declaring package required; a failed `tsc -b` of the declaring project
  makes the merge invisible (props silently lose `t`).
- `exactOptionalPropertyTypes`: `Modal description?: string` rejects
  explicit `undefined` — conditionally spread the prop.
- `ButtonVariant` = `primary | ghost | outline | toolbar` (no `secondary`).
- The package is `@deepseek-ai/dsh-client-locale` (directory
  `packages/client/locale`), not `...ui-locale`.
- jsdom store-driven component tests need `useSyncExternalStore` behind the
  stub hook + `act()` around state changes; grace-window tests use
  `vi.useFakeTimers()` + `act(advanceTimersByTime)`.
- Theme tokens: `--dsw-alias-bg-layer-1..4`, `--dsw-alias-border-l`,
  `--dsw-alias-label-{secondary,tertiary}`, `--dsw-alias-interactive-bg-hover`
  (no `bg-secondary`/`stroke-tertiary`).
- Container TZ is +01:00 — keep timestamp assertions TZ-tolerant.

## Capability ideas (future)

- Quote chips in the composer overlay (visible, deletable chip per open
  quote instead of raw block text in the draft).
- Include-reasoning option (user currently wants reasoning untouched).
- Quote other node kinds (user messages, tool results).
- Range quote (multi-paragraph selection) — the original v1 idea.
