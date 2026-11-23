#!/usr/bin/env bash
# basalt-upgrade-check.sh — READ-ONLY preflight before a Basalt engine upgrade (the agent brain).
# Mirrors strata-upgrade-check.sh for the Basalt clone (~/Apps/Basalt/basalt, origin github.com/jesdga95/basalt).
# Never touches the working tree, bin/, .venv, or the running engine. Fetches ONLY the target tag ref
# (same rule as Strata: never `git fetch --tags`).
# Env: BASALT_HOME (default ~/Apps/Basalt/basalt), TAG (default: newest remote),
#      VARIANT (default 262k2v — picks configs/<variant> for the config-key check).
set -uo pipefail
cd "${BASALT_HOME:-$HOME/Apps/Basalt/basalt}" || exit 1
VARIANT="${VARIANT:-262k2v}"
CFG="configs/basalt-${VARIANT}.json"

cur=$(git describe --tags 2>/dev/null || git rev-parse --short HEAD)
if [ -n "${TAG:-}" ]; then tag="$TAG"
else
  tag=$(git ls-remote --tags origin 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||' | grep -v '\^{}$' | sort -V | tail -1)
  [ -n "$tag" ] || { echo "git ls-remote failed (network?)"; exit 1; }
fi
[ -n "$tag" ] || { echo "no target tag resolved"; exit 1; }
local_sha=$(git rev-parse -q --verify "refs/tags/$tag^{commit}" 2>/dev/null || true)
remote_sha=$(git ls-remote origin "refs/tags/$tag" 2>/dev/null | awk '$2=="refs/tags/'"$tag"'" || $2=="refs/tags/'"$tag"'^{}" {print $1}' | tail -1)
if [ -n "$remote_sha" ] && [ "$local_sha" != "$remote_sha" ]; then
  git fetch --quiet origin "refs/tags/$tag:refs/tags/$tag" --force || { echo "fetch of tag $tag failed"; exit 1; }
fi
echo "current:  $cur"
echo "newest:   $tag"
[ "$(git rev-parse "$tag^{commit}" 2>/dev/null)" = "$(git rev-parse HEAD 2>/dev/null)" ] \
  && echo "== already on the newest tag (nothing to check)" && exit 0

echo "-- changes between (model-relevant lines only) --"
git log --oneline "$cur..$tag" | grep -iE 'flash|qwen4exp|batch|parallel|kv|expert|ram|serve|vram|grammar|vision|spec|changelog' | head -12

# flags: prefer the LIVE engine's actual cmdline; fallback = the variant config file's engine block + model keys.
epid=$(pgrep -f 'Apps/Basalt/basalt/[b]in/basalt --serve' | head -1)
if [ -n "${epid:-}" ]; then
  flags=$(tr '\0' '\n' < "/proc/$epid/cmdline" 2>/dev/null | grep -E '^--' | grep -v '^--serve$' | sort -u)
  echo "flag source: live engine pid $epid"
else
  echo "WARN: engine not running - flag source = $CFG keys"
  flags=$(python3 - "$CFG" <<'PY' 2>/dev/null | sort -u
import json,sys
d=json.load(open(sys.argv[1]))
keys=set(d.get('engine',{}))
for m in d.get('models',[]): keys |= set(m)
print('\n'.join('--'+k for k in keys if k not in ('model',)))
PY
)
fi
missing=0
for f in $flags; do
  if ! git grep -qF -e "$f" "$tag" -- serve/ src/ include/ tools/ 2>/dev/null; then
    echo "MISSING in $tag: $f  <- review by hand before swapping"
    missing=$((missing + 1))
  fi
done
echo "flags checked: $(echo "$flags" | wc -w), missing: $missing"

# serve layout + launcher entry points the serve layer needs (python -m serve.server, bin/basalt serve).
files=$(git ls-tree -r --name-only "$tag" | grep -cE '^(serve/server\.py|serve/config\.py|CMakeLists\.txt)$')
echo "serve/server.py + serve/config.py + CMakeLists.txt present: $files/3"
arch=0
for k in qwen4exp; do
  git grep -q "$k" "$tag" -- CMakeLists.txt src/ 2>/dev/null || { echo "CHECK model arch: $k"; arch=$((arch+1)); }
done
echo "model archs missing: $arch"

# tree state: checkout must be clean on TRACKED files; untracked local additions (configs/, scripts/,
# OPS.md, basalt_config.json, bin/, .venv) survive a checkout untouched.
dirty=$(git status --porcelain --untracked-files=no | wc -l)
echo "tracked files modified: $dirty $([ "$dirty" -gt 0 ] && echo '<- commit or stash before checkout!')"
echo "untracked additions (survive checkout): $(git status --porcelain | grep -c '^??')"

# archive route (preferred over compiling): check release asset + this box's prerequisites.
echo "-- archive route check --"
asset=$(curl -sm12 "https://api.github.com/repos/jesdga95/basalt/releases/tags/$tag" \
  | python3 -c "import json,sys;d=json.load(sys.stdin);a=[x for x in d.get('assets',[]) if 'linux-x64' in x['name']];print(a[0]['browser_download_url'] if a else '')" 2>/dev/null)
if [ -n "$asset" ]; then echo "archive:    $asset"
else echo "archive:    none on this release (use source build below)"; fi
drv=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | cut -d. -f1)
echo "driver:     ${drv:-?} (archive needs R580 branch or newer)"
ldd bin/basalt 2>/dev/null | grep -q libcudart && echo "cudart13:   on the live engine's library path (same the archive needs)" \
  || echo "cudart13:   NOT on bin/basalt's path - verify CUDA 13 runtime libs before using the archive"
diff -q <(git show "$cur:requirements.txt" 2>/dev/null) <(git show "$tag:requirements.txt" 2>/dev/null) >/dev/null 2>&1 \
  && echo "python:     requirements.txt unchanged - existing .venv is reusable" \
  || echo "python:     requirements.txt CHANGED - .venv/bin/pip install -r requirements.txt after checkout"

cat <<EOF
== preflight done. Next (protocol: llm-playground/scripts/dsh-strata-upgrade-protocol.md section D):
   1. cd $PWD && git checkout $tag        # untracked configs/scripts/bin/.venv survive
   2a. ARCHIVE: curl -L -o /tmp/basalt-$tag.tar.gz "$asset"
       tar tzf /tmp/basalt-\$tag.tar.gz | head   # inspect before touching bin/
   2b. SOURCE: cmake -S . -B build -DBASALT_MODELS="qwen4exp;qwen35" -DCMAKE_BUILD_TYPE=Release
       cmake --build build -j                    # writes bin/basalt (new inode; running engine unaffected)
   3. with explicit USER OK, DETACHED: USER_OK=1 bash ~/.dsh/bin/swap-basalt.sh  (chat dark ~3-5 min)
   Rollback = bin/basalt.previous restored + git checkout $cur + restart (swap script prints it).
EOF
