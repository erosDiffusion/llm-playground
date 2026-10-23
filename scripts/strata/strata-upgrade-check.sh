#!/usr/bin/env bash
# strata-upgrade-check.sh — READ-ONLY preflight before a Strata engine upgrade. Never touches the working
# tree, the engine/, or the running brain. Automates the manual compatibility check done by hand on
# 2026-10-21 (14 launch flags + serve CLI + config keys all verified present in v0.2.2). Missing-flag hits
# are advisory — review by hand before swapping.
# Env: STRATA_HOME (default ~/Apps/Strata), TAG (default: newest remote), STRATA_CONFIG (strata-iq3_s.json).
set -uo pipefail
cd "${STRATA_HOME:-$HOME/Apps/Strata}" || exit 1
CFG="${STRATA_CONFIG:-strata-iq3_s.json}"

# Do NOT use `git fetch --tags`: after the 2026-10 upstream history rewrite it rejects every old tag ref
# ("would clobber existing tag") and exits 1. Read the remote tag list, then fetch ONLY the target tag ref.
cur=$(git describe --tags 2>/dev/null || git rev-parse --short HEAD)
if [ -n "${TAG:-}" ]; then tag="$TAG"; else
  tag=$(git ls-remote --tags origin 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||' | grep -v '\^{}$' | sort -V | tail -1)
  [ -n "$tag" ] || { echo "git ls-remote failed (network?)"; exit 1; }
fi
local_sha=$(git rev-parse -q --verify "refs/tags/$tag^{commit}" 2>/dev/null || true)
remote_sha=$(git ls-remote origin "refs/tags/$tag" 2>/dev/null | awk '$2=="refs/tags/'"$tag"'" || $2=="refs/tags/'"$tag"'^{}" {print $1}' | tail -1)
if [ -n "$remote_sha" ] && [ "$local_sha" != "$remote_sha" ]; then
  git fetch --quiet origin "refs/tags/$tag:refs/tags/$tag" --force || { echo "fetch of tag $tag failed"; exit 1; }
fi
echo "current:  $cur"
echo "newest:   $tag"
[ "$(git rev-parse "$tag^{commit}" 2>/dev/null)" = "$(git rev-parse HEAD 2>/dev/null)" ] \
  && echo "== already on the newest tag (nothing to check)" && exit 0

# flags: prefer the LIVE engine's actual cmdline; fallback = the config file's "args" array (same source the
# serve layer uses to launch the engine).
epid=$(pgrep -f 'engine/strata --serve' | head -1)
if [ -n "${epid:-}" ]; then
  flags=$(tr '\0' '\n' < "/proc/$epid/cmdline" 2>/dev/null | grep -E '^--' | grep -v '^--serve$' | sort -u)
  echo "flag source: live engine pid $epid"
else
  echo "WARN: engine not running - flag source = $CFG args"
  flags=$(python3 -c "import json;print('\n'.join(a for a in json.load(open('$CFG'))['args'] if a.startswith('--')))" 2>/dev/null | sort -u)
fi
missing=0
for f in $flags; do
  if ! git grep -qF -e "$f" "$tag" 2>/dev/null; then
    echo "MISSING in $tag: $f  <- review by hand before swapping"
    missing=$((missing + 1))
  fi
done
echo "flags checked: $(echo "$flags" | wc -w), missing: $missing"

files=$(git ls-tree -r --name-only "$tag" | grep -cE '^(serve/server\.py|setup\.py|setup\.sh)$')
echo "serve/server.py + setup.py + setup.sh present: $files/3"
# config keys spot-check: the live config is NEVER touched by a checkout, but the serve layer must know its keys.
misskey=0
for k in vram_elastic vram_reserve_mib max_context; do
  if git grep -qF -e "$k" "$tag" 2>/dev/null || git grep -qF -e "${k/_/-}" "$tag" 2>/dev/null; then :; else
    echo "CHECK config key: $k"; misskey=$((misskey+1)); fi
done
echo "config keys missing: $misskey"
echo "== preflight done. Next (runbook scripts/dsh-strata-upgrade-protocol.md section B): git checkout $tag,"
echo "   warm-build, then (with user OK) swap-strata.sh DETACHED. Packs/models/config are never touched."
