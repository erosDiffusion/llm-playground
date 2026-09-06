#!/usr/bin/env bash

set -euo pipefail

# Run from this script's directory (ComfyUI root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Update ComfyUI repository
echo "Updating ComfyUI repository..."
git pull

# Update all custom node repositories
echo "Updating custom nodes..."
if [[ -f "custom_nodes/update_repos.sh" ]]; then
    bash custom_nodes/update_repos.sh
else
    echo "Warning: custom_nodes/update_repos.sh not found"
fi

# Install/update Python dependencies
"$SCRIPT_DIR/venv/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"

if [[ -d "venv" ]]; then
    # shellcheck disable=SC1091
    source "venv/bin/activate"
elif [[ -d ".venv" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
else
    echo "No virtual environment found in $SCRIPT_DIR (expected venv/ or .venv/)."
    read -r -p "Press Enter to close..." _
    exit 1
fi

# Start ComfyUI Manager
# --enable-triton-backend --disable-pinned-memory --fast cublas_ops
python main.py --enable-manager  --enable-cors-header "*" --enable-manager-legacy-ui 
# --disable-pinned-memory
#--fast-disk
#--reserve-vram 2
# python main.py --enable-manager --enable-triton-backend --disable-pinned-memory --reserve-vram 2 --fast cublas-ops --list-feature-flags --enable-cors-header "*"
