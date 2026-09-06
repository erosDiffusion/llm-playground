# LLM thinking delegation (brainstorming offload)

- **Type:** explore / integrate
- **What:** Ideally one available model should pick up further brainstorming for the various projects and todos — delegate "thinking" work (ideation, tradeoff analysis, design sketches) to a free local or remote LLM instead of spending the primary session's context on it.
- **Why I want to try it:** Frees the main agent's context for execution; idle brains (park brain, cheap local models, remote LLMs) can chew on backlog items in parallel. Pairs naturally with [kanban-board](kanban-board.md) as the task queue.
- **Fits stage:** meta / infra (agent orchestration).
- **Open questions:** which model counts as "available" (park brain :57600? a small local one? remote?) and how do we route to it; what does a delegation request look like (prompt + context budget + expected output format); where do results land (notes/ entry, kanban task comment thread, or new backlog item?).
- **Related:** [kanban-board](kanban-board.md), [multiagent-3080-delegation](multiagent-3080-delegation.md), [backend-engines-comparison](backend-engines-comparison.md).
- **Status log:**
  - 2026-09-06 — added to backlog (watch; user: "we'll see how to implement this later").
