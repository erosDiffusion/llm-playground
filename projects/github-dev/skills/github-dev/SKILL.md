# github-dev — scoped GitHub access runbook

## What you have

- **Wrapper**: `~/.dsh/bin/gh-git` — the ONLY sanctioned path for git against github.com. It injects the stored PAT per invocation (via `http.extraheader`, never written to disk or URLs) and enforces the repo allowlist.
- **Config**: `~/.dsh/github/config.json` — `allowed_repos` (hard scope, `owner/repo` list), `user_name` / `user_email` (commit identity).
- **Token**: `~/.dsh/github/token` — fine-grained PAT, `chmod 600`. Never print it, never echo it into chat, never copy it anywhere else.

## Commands

```
gh-git repos                        list allowed repos
gh-git clone <url> [dir]            scope-checked clone (SSH or HTTPS URL both accepted)
gh-git pull [remote] [ref]          scope-checked pull   (inside a repo)
gh-git push [remote] [args...]      scope-checked push   (inside a repo)
gh-git fetch [remote]               scope-checked fetch  (inside a repo)
gh-git exec <git args...>           any other git command (add/commit/status/log/diff/checkout/rebase...) — identity + credential injected
gh-git config show                  masked config summary
```

Typical flow: `gh-git clone https://github.com/<owner>/<repo>` → work in the dir → commit with `gh-git exec add -A && gh-git exec commit -m "..."` (or plain `git commit` inside the repo is fine too, but push goes through `gh-git push`) → `gh-git push`.

## Hard rules

1. **Scope is enforced by the wrapper.** If a repo is not in `allowed_repos`, `gh-git` refuses. Do NOT work around it with raw `git` + token, `.git/config` URL tricks, or env credentials. If the user wants a new repo added, they edit `allowed_repos` (or ask you to add it — one line in config.json).
2. **Token hygiene.** The token lives only in `~/.dsh/github/token`. Never in URLs, files, commit history, logs, or chat output.
3. **Identity.** Commits are attributed to `user_name`/`user_email` from config (injected by the wrapper). If they're empty, ask the user what name/email should appear on agent commits before the first commit.
4. **No token = stop and ask.** If `~/.dsh/github/token` is missing or empty, follow Setup below — never improvise credentials (no SSH keys, no `gh auth`, no other stored secrets).

## Setup (token/repos not yet configured)

1. User creates (or designates) a GitHub account for the agent and adds it as collaborator on each target repo (Settings → Collaborators; org repos: add as member with a role).
2. On that account: Settings → Developer settings → **Personal access tokens → Fine-grained tokens** → New token:
   - **Repository access**: "Only select repositories" → exactly the target repos (this is the scope).
   - **Permissions**: `Contents` = Read and write; `Pull requests` = Read and write (only if PRs are wanted); `Metadata` = Read-only (automatic).
   - Set an expiry the user is comfortable with.
3. Save the token (`github_pat_...`) to `~/.dsh/github/token`, `chmod 600`.
4. Add the repos to `allowed_repos` in `~/.dsh/github/config.json` and set the commit identity there.
5. Verify: `gh-git config show` + a dry `gh-git clone` of one allowed repo.

## Troubleshooting

- **401/403 on push**: token expired or lacks Contents:write, or repo not in the token's repository access → user re-mints.
- **`repo 'x/y' is NOT in allowed_repos`**: expected refusal — add it to config (with the user's OK) or stop.
- **SSH URL clone fails auth**: use the HTTPS form; the wrapper normalizes `git@github.com:...` → `https://...` automatically, so prefer passing either and let it normalize.
