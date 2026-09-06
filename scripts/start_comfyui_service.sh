#!/usr/bin/env bash
set -euo pipefail

COMFY_DIR="/home/oem/Apps/ComfyUI"
LOG_DIR="${HOME}/.local/state/comfyui"
UPDATE_ON_BOOT="${UPDATE_ON_BOOT:-0}"

mkdir -p "${LOG_DIR}"
cd "${COMFY_DIR}"

if [[ ! -x "${COMFY_DIR}/venv/bin/python" ]]; then
  echo "ComfyUI venv python not found at ${COMFY_DIR}/venv/bin/python" >&2
  exit 1
fi

# Optional maintenance pass. Kept off by default to avoid slow/failing boots when network is unstable.
if [[ "${UPDATE_ON_BOOT}" == "1" ]]; then
  git pull || true
  if [[ -f "custom_nodes/update_repos.sh" ]]; then
    bash custom_nodes/update_repos.sh || true
  fi
  "${COMFY_DIR}/venv/bin/python" -m pip install -r "${COMFY_DIR}/requirements.txt" || true
fi

# COMFYUI_ARGS can be set by systemd service or shell environment.
set -f
EXTRA_ARGS=()
if [[ -n "${COMFYUI_ARGS:-}" ]]; then
  read -r -a EXTRA_ARGS <<< "${COMFYUI_ARGS}"
fi
exec "${COMFY_DIR}/venv/bin/python" main.py "${EXTRA_ARGS[@]}"