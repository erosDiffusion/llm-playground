#!/usr/bin/env bash
# swap-strata.sh — generalized Strata engine swap (drops the agent brain ~90 s-3 min).
# MUST be run DETACHED (setsid / nohup / background job) — this process' parent session dies with the brain.
# Needs explicit USER OK first. Prereq: the repo is on the new tag and warm-build has produced build/strata
# (+ build-vision/bin/strata-vision if vision is used) — this script only stops, finishes `setup.sh --update`
# (no-op build + engine copy + BUILD.json stamp, old binaries kept in engine/.previous), restarts, verifies.
# Env: STRATA_HOME (default ~/Apps/Strata), START_SCRIPT (default START-262k.sh), PORT (default 8080).
# Rollback if the new engine does not come up:
#   cd "$STRATA_HOME" && python3 setup.py --rollback-engine && git checkout <PRE_TAG> && sh "$START_SCRIPT"
set -uo pipefail
cd "${STRATA_HOME:-$HOME/Apps/Strata}" || exit 1
START_SCRIPT="${START_SCRIPT:-START-262k.sh}"
PORT="${PORT:-8080}"
PRE_TAG="${PRE_TAG:-$(git describe --tags 2>/dev/null)}"
LOG="swap-$(date +%Y-%m-%d-%H%M).log"
say() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }

say "swap start (repo: $(git describe --tags 2>/dev/null), build: $(./build/strata --version 2>/dev/null), prev_tag: $PRE_TAG)"

# 1. stop the running brain (SIGINT = the same clean shutdown as Ctrl+C in its terminal)
pid=$(pgrep -f 'serve/server.py --engine strata' | head -1)
if [ -n "${pid:-}" ]; then
  say "SIGINT -> server pid $pid"
  kill -INT "$pid"
  for _ in $(seq 1 60); do ss -ltn 2>/dev/null | grep -q ":$PORT " || break; sleep 1; done
fi
sleep 3
pkill -f 'engine/strata --serve' 2>/dev/null || true
pkill -f 'engine/strata-vision' 2>/dev/null || true
sleep 2

# 2. finish the update: build is a no-op now; copies build/strata(+vision) into engine/,
#    stamps BUILD.json, keeps the old binaries in engine/.previous for --rollback-engine.
sh setup.sh --update >> "$LOG" 2>&1
say "setup.sh --update exit $?"

# 3. start the new brain with the same config, detached
nohup sh "$START_SCRIPT" >> "$(basename "$START_SCRIPT" .sh).log" 2>&1 &
say "launcher $START_SCRIPT launched (pid $!)"

# 4. verify: /health loaded=true, then log what engine is actually running
for _ in $(seq 1 150); do
  if curl -s -m3 "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q '"loaded": true'; then
    say "NEW ENGINE UP:"
    cat engine/BUILD.json >> "$LOG"
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv >> "$LOG" 2>/dev/null
    say "swap OK - resume the chat session in the GUI"
    exit 0
  fi
  sleep 2
done
say "TIMEOUT after 300s - check the launcher log; rollback: python3 setup.py --rollback-engine && git checkout $PRE_TAG && sh $START_SCRIPT"
exit 1
