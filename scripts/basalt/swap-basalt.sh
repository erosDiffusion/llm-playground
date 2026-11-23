#!/usr/bin/env bash
# swap-basalt.sh — atomic Basalt engine swap (drops the agent brain ~3-5 min: kill + engine load ~2-4 min page-lock).
# MUST be run DETACHED (setsid/nohup/background job) — this process' parent session dies with the brain.
# Refuses to run without USER_OK=1 (explicit user OK).
# Prereq (basalt-upgrade-check.sh prints the full flow): the clone is ALREADY on the new tag, and the new
# binaries are staged — either the release archive's bin/ is available (ARCHIVE=/path/to.tar.gz) or
# cmake --build has already rewritten bin/. This script only: saves the old binaries, stages the new ones
# (archive route), path-anchored kill of supervisor+engine, relaunch via scripts/basalt-serve.sh, verify.
# Env: BASALT_HOME (default ~/Apps/Basalt/basalt), VARIANT (default 262k2v — variant name for scripts/basalt-serve.sh),
#      PORT (default 8090), ARCHIVE (optional linux-x64 tar.gz; its bin/* replace bin/ here), PRE_TAG (rollback hint).
# Rollback if the new engine does not come up:
#   cd "$BASALT_HOME" && cp -a bin/basalt.previous/. bin/ && git checkout <PRE_TAG> && nohup scripts/basalt-serve.sh <VARIANT> &
set -uo pipefail
cd "${BASALT_HOME:-$HOME/Apps/Basalt/basalt}" || exit 1
VARIANT="${VARIANT:-262k2v}"
PORT="${PORT:-8090}"
ARCHIVE="${ARCHIVE:-}"
PRE_TAG="${PRE_TAG:-$(git describe --tags 2>/dev/null)}"
[ "${USER_OK:-0}" = "1" ] || { echo "refusing: this kills the running brain. Re-run with USER_OK=1 only after the user approved."; exit 2; }
LOG="$HOME/.local/state/basalt/swap-$(date +%Y-%m-%d-%H%M).log"
mkdir -p "$(dirname "$LOG")"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "swap start (repo: $(git describe --tags 2>/dev/null), prev_tag: $PRE_TAG, variant: $VARIANT, archive: ${ARCHIVE:-none})"

# 1. save the currently deployed binaries (untracked build outputs — rollback copies them back)
mkdir -p bin/basalt.previous
cp -a bin/basalt bin/basalt-bench bin/basalt-probe bin/basalt-vision bin/basalt.previous/ 2>/dev/null
say "old binaries saved to bin/basalt.previous/ (old version: $(bin/basalt --version 2>/dev/null || echo '?'))"

# 2. archive route: stage the release binaries into bin/ (gitignored build output — tree stays clean)
if [ -n "$ARCHIVE" ]; then
  [ -f "$ARCHIVE" ] || { say "ABORT: archive not found: $ARCHIVE"; exit 1; }
  tmp=$(mktemp -d)
  tar xzf "$ARCHIVE" -C "$tmp" || { say "ABORT: extract failed"; rmdir "$tmp"; exit 1; }
  top=$(ls "$tmp")
  [ -x "$tmp/$top/bin/basalt" ] || { say "ABORT: archive has no bin/basalt"; rm -rf "$tmp"; exit 1; }
  cp -a "$tmp/$top/bin/"* bin/ && say "staged binaries from $(basename "$ARCHIVE") ($( "$PWD/bin/basalt" --version 2>/dev/null ))"
  rm -rf "$tmp"
fi

# 3. stop supervisor + engine — path-anchored patterns copied from scripts/basalt-serve.sh (can never match
#    Strata or unrelated processes), then wait for :$PORT to actually free.
pkill -f 'Apps/Basalt/basalt/[.]venv/bin/python -m serve\.server' 2>/dev/null
pkill -f 'Apps/Basalt/basalt/[b]in/basalt --serve' 2>/dev/null
for _ in $(seq 1 60); do curl -s -m 2 -o /dev/null "http://127.0.0.1:$PORT/health" || break; sleep 1; done
say "old brain down (port $PORT freed)"

# 4. relaunch with the same variant config (the launcher is untracked — survives checkouts)
nohup scripts/basalt-serve.sh "$VARIANT" >> "$HOME/.local/state/basalt/serve-$VARIANT.log" 2>&1 &
say "launcher scripts/basalt-serve.sh $VARIANT started (pid $!)"

# 5. verify: /health loaded=true (engine load takes 2-4 min for the page-locked expert copy)
for _ in $(seq 1 180); do
  if curl -s -m3 "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q '"loaded": true'; then
    say "NEW ENGINE UP: $(curl -s -m3 "http://127.0.0.1:$PORT/health" | tr -d '\n ' )"
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv >> "$LOG" 2>/dev/null
    say "swap OK - resume the chat session in the GUI (log: $LOG)"
    exit 0
  fi
  sleep 2
done
say "TIMEOUT after ~360s - check ~/.local/state/basalt/serve-$VARIANT.log"
say "rollback: cp -a bin/basalt.previous/. bin/ && git checkout $PRE_TAG && nohup scripts/basalt-serve.sh $VARIANT &"
exit 1
