# scripts/ — ops script vault

Archived operational scripts. Copies are byte-identical to the source; provenance below. No secrets in any of these (verified by scan on archive date).

| file | what it does | archived from | date |
| --- | --- | --- | --- |
| `start_comfyui_manager.sh` | ComfyUI startup: `git pull` core → run `update_repos.sh` → pip install requirements → launch `main.py --enable-manager --enable-cors-header "*" --enable-manager-legacy-ui` (commented lines show the alternative flag sets: triton backend, pinned memory, fast-disk, reserve-vram) | `$HOME/Progetti/ComfyUI/start_comfyui_manager.sh` | 2026-09-06 |
| `update_repos.sh` | Custom-node updater: per-repo status check; `SKIP_REPOS` (never touch: EulerDiscreteScheduler, erosdiffusion-sigil, enricos-nodes); `DROP_BEFORE_PULL` (reset+clean then ff-pull — encodes which packs are safe to force-update vs. which have local changes worth keeping); parent-repo safety (never resets a repo whose top-level escapes `custom_nodes/`) | `$HOME/Progetti/ComfyUI/custom_nodes/update_repos.sh` | 2026-09-06 |
| `comfy-remote.sh` | curl runner for the remote ComfyUI (`http://192.168.1.34:9000`): submit (wrapped body v0.34+, raw fallback), poll history, download outputs — drop-in for the MCP `run_workflow` when running under the web-lite profile | `$HOME/Apps/deepseek-workspace/comfy-remote.sh` | 2026-09-06 |
| `test-local-flows.sh` | local 8188 flow tester: preflight (reachability, VRAM, queue), aimdo `unload_all` pre/post, submit klein image-edit + H3 video flows, wait, download, append report; env knobs `KLEIN_ONLY`/`H3_ONLY`/`NO_WAIT`/`DRY_RUN` | `$HOME/Apps/deepseek-workspace/test-local-flows.sh` | 2026-09-06 |
| `gh-git` | scoped GitHub git wrapper: clone/pull/push/fetch/exec; injects the stored fine-grained PAT per invocation (`http.extraheader`, never in URLs/files/history); enforces `allowed_repos` from `~/.dsh/github/config.json` as a hard scope; sets commit identity; token-less anonymous reads for public repos | `$HOME/.dsh/bin/gh-git` | 2026-09-06 |
| `remote-boot-systemd.service.template` + `remote-boot-windows.ps1.template` | remote ComfyUI auto-start templates (systemd unit / Windows scheduled task) with `<...>` placeholders; flags mirror `start_comfyui_manager.sh`; `--listen 0.0.0.0` required for LAN access; Windows one includes a watchdog snippet | authored in this vault (templates, no machine specifics) | 2026-09-06 |

> The H3 prompt toolkit moved to [`../projects/h3-prompt-toolkit/`](../projects/h3-prompt-toolkit/) (packaged as a reusable project, 2026-09-06).

## Notes for future runs

- `update_repos.sh` is the most knowledge-dense file here: its `SKIP_REPOS` and `DROP_BEFORE_PULL` lists are the result of real breakage — do not "clean up" duplicates or remove entries without checking why they were added.
- The remote box (192.168.1.34) runs its own ComfyUI install; if its startup command differs from `start_comfyui_manager.sh`, archive that one too (ask the user to paste it — no file access to the remote yet).
