# Kanban board for llm-playground status + LLM task distribution

- **Type:** build
- **What:** A kanban board that visually represents this repo's state (backlog items, projects, scripts) — columns = statuses (want-to-try → investigating → trying → integrated/dropped), with a way to start tasks and leave code comments/instructions that local or remote LLMs can pick up, so work gets distributed across agents.
- **Why I want to try it:** The backlog + projects are markdown-only today; a visual board makes status at-a-glance and turns ideas into assignable, trackable units of work for multiple agent sessions (local brain, park brain, remote LLMs) instead of one session doing everything inline.
- **Fits stage:** meta / infra (repo tooling) — supports every other stage.
- **Open questions:** where does it run (static HTML in the repo? local server? DSH GUI panel?); what is the "code comment picked up by an LLM" contract (file format/location, claim/lock semantics so two agents never grab the same task, completion reporting back to the board); how do remote LLMs get access (gh-git allowlist + task files?).
- **Related:** [llm-thinking-delegation](llm-thinking-delegation.md), [multiagent-3080-delegation](multiagent-3080-delegation.md).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try; user: "we'll work on this project later").
