# dsh-customizations — local DSH harness layer

The user-authored + agent-built customizations that make this DeepSeek Harness deployment behave the way it does. Archived 2026-09-06 from `$HOME/.dsh/`. Text only, secret-scanned clean.

## Contents

| path | what |
| --- | --- |
| `plugins/system-stats.ts` | HOST plugin: `system_stats_local` tool — RAM/VRAM/llama-server footprint snapshot before heavy local work (the preflight tool) |
| `plugins/mcp-gateway.ts` | HOST plugin: on-demand MCP gateway — sessions start with zero MCP context; `mcp_enable`/`mcp_disable` connect/disconnect one MCP server at a time to save context (reuses `@deepseek-ai/dsh-mcp-client` transport) |
| `patches/dsh-video-inline-chat.patch` | app-shell patch: markdown renderer turns `.mp4/.webm/.ogv` image-syntax URLs into inline `<video>` tags (chat video preview) |
| `patches/archive/dsh-checkpoint-lineage-optional.patch` | archived: optional checkpoint-lineage fields in session-projection-cache spec |

**Deliberately NOT archived:** the web profile composition (`$HOME/.dsh/profiles/web/cordis.patch.yml`) — it embeds a private LAN endpoint (remote ComfyUI IP), which repo rules exclude. Its substance: `dsh-base` + `dsh-web-app` bundles, MCP rows for chrome-devtools and remote ComfyUI (routed via `COMFYUI_URL`), the two plugins above registered at host scope, `patchReload: live`.

## Reuse (on a DSH source checkout)

1. Plugins → `$HOME/.dsh/local-plugins/`, then register them in the web profile's composition (host realm).
2. Patches → `$HOME/.dsh/patches/`; after any harness update run `apply-dsh-patches.sh` (idempotent, 3-way merges drifted context, rebuilds client+web, refuses on conflict):
   ```sh
   cp <repo>/projects/dsh-customizations/patches/*.patch "$HOME/.dsh/patches/"
   "$HOME/.dsh/bin/apply-dsh-patches.sh"
   ```
   Note: `dsh-checkpoint-lineage-optional.patch` is archived reference, not auto-applied.
