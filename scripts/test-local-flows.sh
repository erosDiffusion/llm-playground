#!/usr/bin/env bash
# test-local-flows.sh — run the local 8188 image-edit + video flows AS-IS and report.
#
# NO park/resume, NO auto-unload of any LLM model, and NO /free calls: memory
# management is left to you (aimdo GUI "unload ▾" menu = POST /aimdo/unload_all
# or POST /free {"unload_models":true[, "free_memory":true]} for models+node cache).
# If an LLM is holding GPU VRAM, free it YOURSELF first — e.g. ~/.dsh/bin/agent-park.sh
# or unload in the unsloth studio UI — then launch this script.
#
# Flow: SUBMIT all selected flows first (finish before waiting), THEN wait for
# results in order and download outputs.
#
# Usage:
#   bash test-local-flows.sh                # both flows (klein edit, then H3 video)
#   KLEIN_ONLY=1 bash test-local-flows.sh   # image edit only
#   H3_ONLY=1   bash test-local-flows.sh    # video only
#   NO_WAIT=1   bash test-local-flows.sh    # enqueue + print prompt_ids, exit immediately
#   NO_UNLOAD=1 bash test-local-flows.sh    # skip the aimdo VRAM cleanup (pre + post)
# Cleanup uses the reliable aimdo API: POST /aimdo/unload_all (409 if a job is executing),
# verified via GET /aimdo/vram — once BEFORE submissions and once AFTER all flows finish.
# ComfyUI otherwise keeps loaded models resident by design (cache for reuse).
#   DRY_RUN=1   bash test-local-flows.sh    # preflight + plan, submit nothing
#
# Env overrides: COMFY (default http://127.0.0.1:8188), KLEIN_FILE, H3_FILE,
#                KLEIN_MAXC/KLEIN_INTV, H3_MAXC/H3_INTV (wait budget = MAXC*INTV seconds)
#                NO_UNLOAD=1 to skip the post-flow aimdo cleanup (default: auto-unload after flows)
set -uo pipefail

# env vars are case-sensitive — accept lowercase variants too (h3_ONLY etc.)
H3_ONLY=${H3_ONLY:-${h3_only:-0}}
KLEIN_ONLY=${KLEIN_ONLY:-${klein_only:-0}}
NO_WAIT=${NO_WAIT:-${no_wait:-0}}
DRY_RUN=${DRY_RUN:-${dry_run:-0}}

COMFY=${COMFY:-http://127.0.0.1:8188}
WS=/home/oem/Apps/deepseek-workspace
RUNS=$WS/comfyui/local/runs
OUTDIR=$WS/generated/video-test
REPORT=$WS/work/flow-test-report.md
KLEIN_FILE=${KLEIN_FILE:-$RUNS/01-klein-edit.json}
H3_FILE=${H3_FILE:-$RUNS/02-h3-video.json}
KLEIN_MAXC=${KLEIN_MAXC:-60};  KLEIN_INTV=${KLEIN_INTV:-5}    # ~5 min budget (takes ~15 s on GPU)
H3_MAXC=${H3_MAXC:-90};        H3_INTV=${H3_INTV:-30}          # ~45 min budget (video takes 10-20+ min; slower on CPU)

mkdir -p "$OUTDIR"
log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ---------- preflight (report only, never block) ----------
if ! curl -sf -m 5 "$COMFY/system_stats" >/dev/null 2>&1; then
  echo "FATAL: ComfyUI not reachable at $COMFY — is it running?" >&2
  exit 2
fi
VRAM_FREE=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
log "preflight: ComfyUI up; VRAM free = ${VRAM_FREE} MiB (klein ~10-15GB, H3 ~22-27GB)"
if [ "${VRAM_FREE:-0}" -lt 15000 ]; then
  log "NOTE: low VRAM — flows may OOM or fall back to CPU (slow but works; see the 23:53 H3 success on CPU)."
fi
QUEUE=$(curl -s -m 5 "$COMFY/queue" | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d.get('queue_running',[]))+len(d.get('queue_pending',[])))" 2>/dev/null || echo '?')
log "preflight: queue items = $QUEUE"

# ---------- submit (no waiting) ----------
submit_flow() { # <runfile> -> sets SUBMIT_PID; 0 accepted / 1 failed (reason logged)
  local runfile=$1 label resp pid kind curl_rc=0 BODY
  label=$(basename "$runfile")
  if [ ! -f "$runfile" ]; then log "FAIL $label: file not found: $runfile"; return 1; fi
  # ComfyUI /prompt wants the body WRAPPED: {"client_id":..., "prompt": <api-format>}
  BODY=$(python3 -c "import json,sys
wf=json.load(open(sys.argv[1]))
if not any(isinstance(v,dict) and 'class_type' in v for v in wf.values()):
    sys.exit('run file is not API format (no class_type entries)')
print(json.dumps({'client_id':'test-local-flows','prompt':wf}))" "$runfile") || { log "FAIL $label: bad run file (not API format)"; return 1; }
  resp=$(curl -s -m 120 -X POST "$COMFY/prompt" -H 'Content-Type: application/json' -d "$BODY") || curl_rc=$?
  if [ "$curl_rc" -ne 0 ]; then
    log "FAIL $label: TRANSPORT error (curl rc=$curl_rc) — the server MAY still have accepted the job; check queue/GUI before resubmitting!"
    return 1
  fi
  kind=$(echo "$resp" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('notjson'); sys.exit(0)
if d.get('node_errors'): print('rejected')
elif d.get('prompt_id'): print('accepted')
else: print('other')" 2>/dev/null || echo notjson)
  case "$kind" in
    accepted)
      pid=$(echo "$resp" | python3 -c "import json,sys;print(json.load(sys.stdin)['prompt_id'])")
      SUBMIT_PID=$pid
      log "submitted $label -> prompt_id $pid"
      return 0;;
    rejected)
      log "FAIL $label: server REJECTED the graph (syntax/wiring):"
      echo "$resp" | python3 -m json.tool 2>/dev/null | head -60 | sed 's/^/    /' || echo "$resp" | head -c 800
      return 1;;
    *)
      log "FAIL $label: unexpected response: $(echo "$resp" | head -c 500)"
      return 1;;
  esac
}

# ---------- wait + download (after all submissions) ----------
wait_flow() { # <prompt_id> <label> <max_checks> <interval_s> <canonical_prefix> -> 0/1
  local pid=$1 label=$2 maxc=$3 intv=$4 canon=$5 R ok=""
  for i in $(seq 1 "$maxc"); do
    R=$(curl -s -m 10 "$COMFY/history/$pid") || R=""
    if echo "${R:-}" | grep -q '"status_str"'; then
      ok=$(echo "$R" | python3 -c "import json,sys
print(json.load(sys.stdin).get('$pid',{}).get('status',{}).get('status_str','?'))")
      break
    fi
    sleep "$intv"
  done
  if [ "${ok:-}" = "success" ]; then
    log "JOB $label succeeded (prompt_id $pid)"
    download_output "$pid" "$canon" || { log "WARN $label: job succeeded but output download failed"; return 1; }
    return 0
  fi
  if [ "${ok:-}" = "error" ]; then
    log "JOB $label FAILED (server error):"
    echo "$R" | python3 -c "import json,sys
d=json.load(sys.stdin)
e=d[list(d)[0]]
print(json.dumps(e.get('status',{}).get('messages',[]), indent=1)[:2500])" 2>/dev/null | sed 's/^/    /'
    return 1
  fi
  log "JOB $label TIMED OUT after $((maxc*intv)) s — still running? check the ComfyUI GUI (prompt_id $pid)"
  return 1
}

download_output() { # <prompt_id> <canonical_prefix> -> saves into OUTDIR; 0/1
  local pid=$1 canon=$2 info fn sf ty ext
  info=$(curl -s -m 10 "$COMFY/history/$pid" | python3 -c "
import json,sys
d=json.load(sys.stdin)
e=d[list(d)[0]]
def walk(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='filename' and isinstance(v,str):
                yield v, o.get('subfolder',''), o.get('type','output')
            else:
                yield from walk(v)
    elif isinstance(o,list):
        for x in o: yield from walk(x)
for f,s,t in walk(e.get('outputs',{})):
    print(f,s,t); break")
  if [ -z "${info:-}" ]; then log "no output file found for $pid"; return 1; fi
  read -r fn sf ty <<< "$info"
  ext=${fn##*.}
  curl -s -m 600 -o "$OUTDIR/$fn" "$COMFY/view?filename=$fn&subfolder=$sf&type=$ty" || { log "download failed: $fn"; return 1; }
  [ -s "$OUTDIR/$fn" ] || { log "download empty: $fn"; return 1; }
  cp -f "$OUTDIR/$fn" "$OUTDIR/${canon}.${ext}"
  log "saved $(basename "$OUTDIR/$fn") ($(stat -c%s "$OUTDIR/$fn") bytes) + canonical ${canon}.${ext}"
  return 0
}

# ---------- main: submit everything first, then wait ----------
KLEIN_RESULT="skipped"; H3_RESULT="skipped"
KLEIN_PID=""; H3_PID=""

if [ "${DRY_RUN:-0}" = "1" ]; then
  log "DRY_RUN plan:"
  [ "${H3_ONLY:-0}" != "1" ] && log "  1. submit $KLEIN_FILE (klein image edit)"
  [ "${KLEIN_ONLY:-0}" != "1" ] && log "  2. submit $H3_FILE (H3 video)"
  log "  then wait for results in order and download to $OUTDIR"
  log "DRY_RUN complete — nothing was submitted."
  exit 0
fi

# ---------- pre-flow cleanup (reliable aimdo API; 409 if a job is executing) ----------
if [ "${NO_UNLOAD:-0}" != "1" ]; then
  U=$(curl -s -m 10 -X POST "$COMFY/aimdo/unload_all")
  V=$(curl -s -m 5 "$COMFY/aimdo/vram" | python3 -c "import json,sys;print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo '?')
  log "pre-flow: aimdo unload_all -> $U (models still loaded: $V)"
fi

# phase 1: submissions (finish before waiting)
if [ "${H3_ONLY:-0}" != "1" ]; then
  SUBMIT_PID=""
  if submit_flow "$KLEIN_FILE"; then KLEIN_PID=$SUBMIT_PID; else KLEIN_RESULT="FAIL at submit (details above)"; fi
fi
if [ "${KLEIN_ONLY:-0}" != "1" ]; then
  SUBMIT_PID=""
  if submit_flow "$H3_FILE"; then H3_PID=$SUBMIT_PID; else H3_RESULT="FAIL at submit (details above)"; fi
fi

if [ "${NO_WAIT:-0}" = "1" ]; then
  log "NO_WAIT: submissions done — jobs are queued/running on $COMFY."
  [ -n "$KLEIN_PID" ] && log "  klein prompt_id: $KLEIN_PID"
  [ -n "$H3_PID" ]    && log "  H3    prompt_id: $H3_PID"
  log "check later: curl $COMFY/history/<prompt_id>  (or the ComfyUI GUI)"
  exit 0
fi

# phase 2: wait for results in order
if [ -n "$KLEIN_PID" ]; then
  if wait_flow "$KLEIN_PID" "klein-edit" "$KLEIN_MAXC" "$KLEIN_INTV" "01-klein-sideview"; then
    KLEIN_RESULT="PASS -> generated/video-test/01-klein-sideview.* (prompt_id $KLEIN_PID)"
  else
    KLEIN_RESULT="FAIL at wait/download (details above)"
  fi
fi
if [ -n "$H3_PID" ]; then
  if wait_flow "$H3_PID" "h3-video" "$H3_MAXC" "$H3_INTV" "02-rich-hero"; then
    H3_RESULT="PASS -> generated/video-test/02-rich-hero.* (prompt_id $H3_PID)"
  else
    H3_RESULT="FAIL at wait/download (details above)"
  fi
fi

# ---------- post-flow cleanup (reliable aimdo API, safe: 409 if a job is still executing) ----------
if [ "${NO_UNLOAD:-0}" != "1" ] && { [ -n "$KLEIN_PID" ] || [ -n "$H3_PID" ]; }; then
  U=$(curl -s -m 10 -X POST "$COMFY/aimdo/unload_all")
  V=$(curl -s -m 5 "$COMFY/aimdo/vram" | python3 -c "import json,sys;print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo '?')
  log "post-flow: aimdo unload_all -> $U (models still loaded: $V)"
fi

# ---------- report ----------
SUMMARY="
## $(date '+%Y-%m-%d %H:%M') flow test

- klein image-edit: **${KLEIN_RESULT}**
- H3 video: **${H3_RESULT}**
- VRAM free at start: ${VRAM_FREE} MiB
"
echo "$SUMMARY" >> "$REPORT"
log "report appended to $REPORT"
echo
echo "================ SUMMARY ================"
echo "  klein image-edit : $KLEIN_RESULT"
echo "  H3 video         : $H3_RESULT"
echo "=========================================="

case "$KLEIN_RESULT/$H3_RESULT" in
  *FAIL*) exit 1;;
esac
exit 0
