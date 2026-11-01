# Queued-prompt routing to external subagent lanes — feasibility

Question (2026-11-01): prompts pile up in the Web chat queue (this box
defaults to Queue, not Steer — see submission-settings.ts:20-21). Could
a plugin parse each queued prompt and dispatch it to an idle Copilot /
Antigravity lane instead of waiting for the main conversation? Probe:
harness checkout at `dsh-v0.2.1-rc.2` (`git describe --tags`, 2026-11-01).

## The queue today

- A Web submit arrives as `prompt` with `mode: 'queue' | 'steer'` and
  source `kind: 'user'` (api/session-controller/src/types.ts:348,418,
  index.ts:461,480). Queue → `agent.followup()` (inbox `next-turn`), Steer
  → `agent.steer()` (`next-step`) (commands.ts:350-351; agent.ts:163-169).
- Storage is durable: each inbox change appends one `agent/inbox/spliced`
  session event; the `inbox` projection fold rebuilds pending lists
  (core/agent-loop/src/inbox.ts:27-65,235).
- Delivery is lazy: the loop `claim()`s at the next step/turn boundary —
  all of `next-step` plus ONE `next-turn` message per boundary
  (agent.ts:267-271,315-318; inbox.ts:109-114); an idle agent wakes first.
- Items stay user-mutable until claimed: QueueDock edit / remove /
  promote run via `updateQueue` (commands.ts:469-489); Stop keeps the queue.

## Seams

- Observing "a message was queued" works TODAY, no harness change: each
  insertion emits agent-scoped `agent/inbox/inserted` with
  `{ agent, message }` (inbox.ts:240; runtime-types.ts:288; example
  subscriber goal/goal-round-driver/src/index.ts:315).
- Filter by `message.source.kind`: browser prompts are `user`
  (session-controller types.ts:418); relays, notices, injected context
  carry other kinds (subagent/src/continuation-messages.ts:30-43).
  `agent/inbox/claimed` (:299) = delivered, `discarded` (:307) = canceled.
- Gap: the live event omits which list was hit; tell Queue from Steer
  via the durable splice using `ctx.on('session/event', …)` (agent.ts:334).
  Smallest seam: one `target` field on the live event payload.
- Programmatic queueing precedents: schedule/src/runtime.ts:123,
  experimental/webhook/src/session.ts:153 call `agent.followup(…)`.

## Spawning external lanes programmatically

- Each lane = provider row (`@deepseek-ai/dsh-subagent-acp`, providerName
  `copilot-acp` / `antigravity-acp` / `agy-opus-acp`) + tool row
  (`dsh-tool-subagent`) — web-lite/cordis.patch.yml:36-107 (read 2026-11-01).
- The tool is a thin wrapper: inject `subagents`, then
  `ctx.subagents.startActivation({ provider, request })`
  (subagent/tool-subagent/src/index.ts:43,330). Any plugin injecting the
  same service can call it — a plugin CAN start those lanes.
- `startActivation` requires the exact live parent Agent
  (subagent/subagent/src/index.ts:277-278) — the inbox event supplies one.
- External children run once, share the `maxActiveSubagents` (8) pool,
  and emit auditable `subagent/start` / `subagent/end` (index.ts:158,166).

## Classifying cheaply

The gate is already a CLI: `~/.dsh/bin/acp-budget plan LANE N` → GO/NO-GO
against the floors (5h ≥20%, weekly ≥25%, Copilot hold 20 premium
requests/month; acp-budget:35, measured 2026-11-01). Classifier cost:

- explicit marker (`route?`) + plain rules — free, and preferred;
- local embeddings qwen3-embed :8092 or park-thin :57600 — ~free money,
  GPU cost: Strata-full leaves ~2.4 GB VRAM (nvidia-smi 2026-10-31), so
  only a tiny model fits without flexing Strata;
- Strata :8080 itself — money-free but it IS the main agent; a call
  competes for its 2 conversation slots; last resort;
- Antigravity `flash-low` lane as classifier — 1.0 notch/5h + 0.5
  weekly per job (acp-budget PRICE 27-34): cheapest external option;
- Copilot `mai-code` — 0.25 premium requests = 1/80 of the monthly
  hold PER MESSAGE; never classify with Copilot.

Ladder: marker → local rules → external classifier only when the pool has
room for TWO jobs (the classification and the actual work).

## Risks

- **Double-spending quota** — routing decisions link to no ledger.
  Mitigate: `acp-budget plan LANE N` before every dispatch, append to
  ~/.dsh/quota/acp-ledger.tsv, cap N jobs per message and per hour.
- **Acting on a message meant for cancel** — the queue is mutable until
  claimed (commands.ts:469-489). Re-check pending at activation; on
  `agent/inbox/discarded` cancel via the child's `dispose()`; human press.
- **Secrets to third parties** — Copilot / Antigravity are GitHub /
  Google. Env creds are scrubbed at spawn
  (subagent-acp/src/run.ts:344) but the PROMPT TEXT ships. Mitigate:
  redaction, per-folder lane allowlist, human route confirmation.
- **Loops** — a child's settlement notice re-enters the parent queue as
  a user-role message with source `subagent-settled`
  (subagent/src/manager.ts:1187-1199). Mitigate: route only
  `source.kind === 'user'`, dedupe by `message.id`, cap routed per turn.

## Verdict and v0

**Feasible today, plugin-only — no harness source change**: observe,
classify, gate, act are all existing surfaces. Honest v0 = human press:

1. extend the existing `dsh-quota-panel` bundle (workspace
   `dsh-quota-panel/`, host row + `client.js`): the host half listens
   to `agent/inbox/inserted` and labels pending items routable / lane;
2. the client half shows a "route this to <lane>" button beside the
   queued item (QueueDock area);
3. the press runs `acp-budget plan LANE N`, then `startActivation`,
   and reports `subagent/end`; dry-run (label only) is the default.

If automation later needs queue-vs-steer live, the smallest seam is one
`target` field on `agent/inbox/inserted` — no loop change. Biggest
blocker: policy, not plumbing — queued text is user-mutable
until claimed and leaves the box to a third party, so auto-dispatch
trades trust and quota for latency; keep the human press until
redaction is proven and the floors hold by construction.
