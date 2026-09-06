#!/usr/bin/env bash
# comfy-remote.sh — curl-based remote ComfyUI runner (drop-in for mcp__comfyui__run_workflow)
# Needed when running under the web-lite profile (no MCP tools).
# Usage:  comfy-remote.sh run <workflow.json> [out_dir]     # submit, wait, download outputs
#         comfy-remote.sh submit <workflow.json>            # submit only, print prompt_id
# Env:    COMFY_REMOTE (default http://192.168.1.34:8188), MAX_WAIT_S (default 900)
set -uo pipefail
COMFY=${COMFY_REMOTE:-http://192.168.1.34:8188}
MAX_WAIT_S=${MAX_WAIT_S:-900}

submit() { # <wf> -> prints prompt_id on stdout; tries wrapped body first (v0.34+), then raw
  local wf=$1 resp rc=0
  local body
  body=$(python3 -c "import json,sys;print(json.dumps({'client_id':'comfy-remote','prompt':json.load(open(sys.argv[1]))}))" "$wf") || return 1
  resp=$(curl -s -m 120 -X POST "$COMFY/prompt" -H 'Content-Type: application/json' -d "$body") || rc=$?
  if [ $rc -ne 0 ] || ! echo "$resp" | grep -q '"prompt_id"'; then
    resp=$(curl -s -m 120 -X POST "$COMFY/prompt" -H 'Content-Type: application/json' -d "$(cat "$wf")") || { echo "submit failed (transport)" >&2; return 1; }
  fi
  if ! echo "$resp" | grep -q '"prompt_id"'; then
    echo "submit rejected:" >&2; echo "$resp" | head -c 600 >&2; return 1
  fi
  echo "$resp" | python3 -c "import json,sys;print(json.load(sys.stdin)['prompt_id'])"
}

wait_and_fetch() { # <pid> <out_dir>
  local pid=$1 outdir=$2 deadline=$(( $(date +%s) + MAX_WAIT_S )) R ok=""
  while [ "$(date +%s)" -lt "$deadline" ]; do
    R=$(curl -s -m 10 "$COMFY/history/$pid") || R=""
    if echo "${R:-}" | grep -q '"status_str"'; then
      ok=$(echo "$R" | python3 -c "import json,sys;print(json.load(sys.stdin).get('$pid',{}).get('status',{}).get('status_str','?'))")
      break
    fi
    sleep 5
  done
  if [ "${ok:-}" != "success" ]; then
    echo "job $pid: ${ok:-TIMEOUT after ${MAX_WAIT_S}s}" >&2
    [ -n "${R:-}" ] && echo "$R" | python3 -c "import json,sys;d=json.load(sys.stdin);e=d[list(d)[0]];print(json.dumps(e.get('status',{}).get('messages',[]),indent=1)[:2000])" 2>/dev/null >&2
    return 1
  fi
  mkdir -p "$outdir"
  echo "$R" | python3 -c "
import json,sys,subprocess,os
d=json.load(sys.stdin); e=d[list(d)[0]]
def walk(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='filename' and isinstance(v,str): yield v,o.get('subfolder',''),o.get('type','output')
            else: yield from walk(v)
    elif isinstance(o,list):
        for x in o: yield from walk(x)
for fn,sf,ty in walk(e.get('outputs',{})):
    url=f'$COMFY/view?filename={fn}&subfolder={sf}&type={ty}'
    subprocess.run(['curl','-s','-m','600','-o',os.path.join('$outdir',fn),url],check=True)
    print('saved:',os.path.join('$outdir',fn))"
}

cmd=${1:-run}; shift || true
case "$cmd" in
  submit) pid=$(submit "${1:?workflow.json required}") || exit 1; echo "$pid";;
  run)    outdir=${2:-generated/remote}; pid=$(submit "${1:?workflow.json required}") || exit 1
          echo "prompt_id: $pid — waiting (max ${MAX_WAIT_S}s)..."
          wait_and_fetch "$pid" "$outdir";;
  *) echo "usage: $0 {run|submit} <workflow.json> [out_dir]" >&2; exit 2;;
esac
