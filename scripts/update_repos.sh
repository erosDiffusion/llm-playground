#!/usr/bin/env bash
set -uo pipefail
IFS=$'\n\t'

# Usage: update_repos.sh [base_dir]
# Defaults to /home/oem/Progetti/ComfyUI/custom_nodes

BASE_DIR="${1:-/home/oem/Progetti/ComfyUI/custom_nodes}"

if [ ! -d "${BASE_DIR}" ]; then
  echo "Base directory not found: ${BASE_DIR}" >&2
  exit 1
fi

echo "Scanning repositories in: ${BASE_DIR}"

# Color support: enabled by default. Set NO_COLOR=1 to disable.
if [ "${NO_COLOR:-0}" != "0" ]; then
  BOLD=""
  RED=""
  GREEN=""
  YELLOW=""
  BLUE=""
  NC=""
else
  BOLD="\033[1m"
  RED="\033[31m"
  GREEN="\033[32m"
  YELLOW="\033[33m"
  BLUE="\033[34m"
  NC="\033[0m"
fi

# Repositories to skip (absolute paths)
SKIP_REPOS=(
  "/home/oem/Progetti/ComfyUI/custom_nodes/ComfyUI-EulerDiscreteScheduler"
  "/home/oem/Progetti/ComfyUI/custom_nodes/ComfyUI-erosdiffusion-sigil"
  "/home/oem/Progetti/ComfyUI/custom_nodes/ComfyUI-enricos-nodes"
)

# Repositories (by folder name) for which local changes should be dropped before pulling
# Add folder names here, e.g. (licon-msr)
DROP_BEFORE_PULL=(
  "licon-msr"
  "comfyui-minimaxh3-easy"
  "ComfyUI-MemoryVisualization"
  "ComfyUI-INT8-Fast"
  "comfyui-hrnodes"
  "ComfyUI_Comfyroll_CustomNodes"
  "comfyui-vrgamedevgirl"
  "ComfyUI-VFI"
  "ComfyUI-YCNodes-MiniMax-H3"
  "ComfyUI-MiniMax-H3-SPEED"
  "Comfyui_Minimax_h3_latent_Upscaler"
  "ComfyUI_frontend_vue_basic"
  "ComfyUI-RBG-SmartSeedVariance"
  "minimax-h3-longmedia"
  "licon-msr"
  "comfyui-vrgamedevgirl"
  "ComfyUI_MiniMax_H3_Extender"
  "Comfyui_Minimax_h3_latent_Upscaler"
  "ComfyUI_Comfyroll_CustomNodes"
  "/ComfyUI_Comfyroll_CustomNodes"
  "ComfyUI_MiniMax_H3_Extender"
  "Comfyui_Minimax_h3_latent_Upscaler"
  "ComfyUI-PlagueKind-Nodes"
  "ComfyUI-RBG-SmartSeedVariance"
  "comfyui-vrgamedevgirl"
  "ComfyUI-YCNodes-MiniMax-H3"
  "/licon-msr"
  "minimax-h3-longmedia"


)

for dir in "${BASE_DIR}"/*/; do
  [ -d "${dir}" ] || continue
  repo_dir="${dir%/}"
  # Skip explicit paths
  skip=false
  for s in "${SKIP_REPOS[@]}"; do
    if [ "${repo_dir}" = "${s}" ]; then
      skip=true
      break
    fi
  done
  if [ "$skip" = true ]; then
    printf "%b\n" "${YELLOW}Skipping ${repo_dir}: configured to skip${NC}"
    continue
  fi

  if ! git -C "${repo_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf "%b\n" "${YELLOW}Skipping ${repo_dir}: not a git repository${NC}"
    continue
  fi

  # Determine repository top-level. If this folder is part of a larger repository
  # (top_level != repo_dir), treat it as a subdirectory of a parent repo. We will
  # NOT perform destructive operations (reset/clean) or automatic pulls on the
  # parent repo to avoid touching files outside ${BASE_DIR} (e.g., start_comfyui_manager.sh).
  top_level=$(git -C "${repo_dir}" rev-parse --show-toplevel 2>/dev/null || true)
  if [ "${top_level}" != "${repo_dir}" ]; then
    rel_path=${repo_dir#${top_level}/}
    printf "%b\n" "${YELLOW}Repository: ${repo_dir} (part of parent repo: ${top_level})${NC}"

    # Show only status lines that are inside the subfolder (relative path starts with rel_path)
    statuses=$(git -C "${top_level}" status --porcelain | while IFS= read -r line; do
      path="${line:3}"
      case "${path}" in
        ${rel_path}/*|${rel_path}) printf "%s\n" "${line}" ;;
      esac
    done)

    if [ -n "${statuses}" ]; then
      branch=$(git -C "${repo_dir}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "(unknown)")
      printf "  %b\n" "${RED}Pending local changes inside ${rel_path} on branch: ${branch}${NC}"
      printf "  %b\n" "${YELLOW}Changed/unstaged/untracked files inside ${rel_path}:${NC}"
      printf "%s\n" "${statuses}" | sed -e 's/^/    /'
      printf "  %b\n" "${YELLOW}Note: ${repo_dir} is part of parent repo ${top_level}; automatic pull/reset is skipped to avoid touching files outside ${BASE_DIR}.${NC}"
    else
      printf "  %b\n" "${GREEN}No local changes inside ${rel_path}. Automatic pull is skipped for parent repos to avoid touching files outside ${BASE_DIR}. To update run: git -C ${top_level} pull (manually)${NC}"
    fi

    continue
  fi

  printf "%b\n" "${BOLD}${BLUE}Repository: ${repo_dir}${NC}"

  # Check for any local changes (including untracked files)
  # Check for any local changes (including untracked files)
  if git -C "${repo_dir}" status --porcelain | grep -q .; then
    branch=$(git -C "${repo_dir}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "(unknown)")
    printf "  %b\n" "${RED}Pending local changes on branch: ${branch}${NC}"
    printf "  %b\n" "${YELLOW}Changed/unstaged/untracked files:${NC}"
    git -C "${repo_dir}" status --porcelain | sed -e 's/^/    /'

    # If this repo is listed in DROP_BEFORE_PULL, drop local changes and continue to pull
    base_name=$(basename "${repo_dir}")
    drop=false
    for d in "${DROP_BEFORE_PULL[@]}"; do
      if [ "${base_name}" = "${d}" ]; then
        drop=true
        break
      fi
    done

    if [ "$drop" = true ]; then
      printf "  %b\n" "${YELLOW}Dropping local changes for ${base_name} and attempting pull${NC}"
      # Double-check top-level again before destructive actions
      top_level=$(git -C "${repo_dir}" rev-parse --show-toplevel 2>/dev/null || true)
      if [ "${top_level}" != "${repo_dir}" ]; then
        printf "%b\n" "${RED}Safety: top-level mismatch for ${repo_dir} (=${top_level}) — not dropping changes${NC}" >&2
        continue
      fi

      if git -C "${repo_dir}" reset --hard && git -C "${repo_dir}" clean -fd; then
        printf "  %b\n" "${GREEN}Local changes dropped${NC}"
      else
        printf "%b\n" "${RED}Failed to drop local changes for ${repo_dir}${NC}" >&2
        continue
      fi
    else
      printf "  %b\n" "${YELLOW}Not configured to drop changes — skipping pull${NC}"
      continue
    fi
  fi

  # Ensure there's an upstream configured before pulling
  if git -C "${repo_dir}" rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
    printf "  %b\n" "${GREEN}Clean — pulling latest from remote${NC}"
    if ! git -C "${repo_dir}" pull --ff-only; then
      printf "%b\n" "${RED}git pull failed for ${repo_dir}${NC}" >&2
    fi
  else
    printf "  %b\n" "${YELLOW}No upstream configured — skipping pull${NC}"
  fi
done

printf "%b\n" "${BOLD}${BLUE}Done.${NC}"
