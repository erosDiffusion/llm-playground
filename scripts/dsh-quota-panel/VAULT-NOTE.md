Vault copy of the workspace bundle `dsh-quota-panel` (source of truth stays at
/home/oem/Apps/deepseek-workspace/dsh-quota-panel, copied 2026-11-01).

Purpose: after a DSH upgrade or a lost workspace folder the panel can be rebuilt:
  1. copy these files back to a workspace folder (never install a profile bundle from /tmp),
  2. add a link: dependency + a dsh.profile.bundles row in ~/.dsh/profiles/web-lite/package.json,
  3. pnpm install in that profile dir, then verify with pnpm run dsh --profile web-lite --dump-config.

What it does: reads Antigravity pool state with the LOCAL agy slash command (/usage, costs no
pool counter), counts running agent processes with ps (no provider call), reads the Strata
engine slot report from GET 127.0.0.1:8080/slots (read-only, never starts or stops anything),
and prices one more job per lane by parsing the PRICE table owned by ~/.dsh/bin/acp-budget.
