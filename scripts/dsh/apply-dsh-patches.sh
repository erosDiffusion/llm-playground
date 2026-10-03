#!/usr/bin/env bash
# Apply local DSH patches to the harness checkout. Self-contained: works from
# any extraction of the dsh-local-patches kit (patches/ next to bin/), or from
# the standing location ~/.dsh/. Run after ANY update flow (git pull, tag
# checkout, fresh re-clone):
#   bash apply-dsh-patches.sh            # apply + rebuild
#   bash apply-dsh-patches.sh --install  # also sync patches+script to ~/.dsh/
# Idempotent: already-applied patches are skipped; drifted context is merged
# with --3way and reported for manual review. Rebuilds host + client + web.
set -euo pipefail

CHECKOUT="${DSH_CHECKOUT:-/home/oem/Apps/deepseek-harness}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Patch dir: explicit env > kit layout (../patches beside this script) > standing location.
if [ -n "${DSH_PATCH_DIR:-}" ]; then
  PATCH_DIR="$DSH_PATCH_DIR"
elif [ -d "$SCRIPT_DIR/../patches" ]; then
  PATCH_DIR="$SCRIPT_DIR/../patches"
else
  PATCH_DIR="$HOME/.dsh/patches"
fi

do_install=0
for arg in "$@"; do
  case "$arg" in
    --install) do_install=1 ;;
    *) echo "unknown option: $arg (supported: --install)" >&2; exit 2 ;;
  esac
done

if [ "$do_install" -eq 1 ]; then
  mkdir -p "$HOME/.dsh/patches" "$HOME/.dsh/bin"
  cp -f "$PATCH_DIR"/*.patch "$HOME/.dsh/patches/"
  cp -f "$SCRIPT_DIR/apply-dsh-patches.sh" "$HOME/.dsh/bin/apply-dsh-patches.sh"
  chmod +x "$HOME/.dsh/bin/apply-dsh-patches.sh"
  echo "installed: $(ls "$HOME/.dsh/patches" | wc -l) patch(es) -> ~/.dsh/patches/, script -> ~/.dsh/bin/"
fi

if [ ! -d "$CHECKOUT/.git" ]; then
  echo "error: $CHECKOUT is not a git checkout (set DSH_CHECKOUT)" >&2
  exit 1
fi
cd "$CHECKOUT"

applied=0
skipped=0
conflicts=0
for patch in "$PATCH_DIR"/*.patch; do
  [ -e "$patch" ] || continue
  name=$(basename "$patch")
  if git apply --check --reverse "$patch" >/dev/null 2>&1; then
    echo "skip   $name (already applied)"
    skipped=$((skipped + 1))
  elif git apply --check "$patch" >/dev/null 2>&1; then
    git apply "$patch"
    echo "applied $name"
    applied=$((applied + 1))
  else
    # Context drifted: attempt a 3-way merge, leave the tree for review.
    if git apply --3way "$patch" >/dev/null 2>&1; then
      echo "merged  $name (3-way — review with: git status)"
      applied=$((applied + 1))
    else
      echo "CONFLICT $name — resolve manually: git apply --3way $patch" >&2
      conflicts=$((conflicts + 1))
    fi
  fi
done

if [ "$conflicts" -gt 0 ]; then
  echo "error: $conflicts patch(es) conflicted; NOT rebuilding until resolved." >&2
  exit 1
fi

if [ "$applied" -eq 0 ]; then
  echo "nothing to apply ($skipped already in place); skipping rebuild."
  exit 0
fi

echo "rebuilding host libs + client libs + web shell..."
set -o pipefail
# Workspace install first: patches may introduce a new workspace package
# (e.g. dsh-quote-selection.patch adds packages/client/ui-quote) that must be
# linked into node_modules before the tsc project references can resolve it.
# Idempotent and fast when nothing changed.
pnpm install 2>&1 | tail -2
# Host face first: some local patches touch the node/host half (settings
# registration, host services). Its artifacts are regenerated here and on the
# next dsh boot; the client face then rebuilds the rest + browser bundles.
pnpm build:lib:host 2>&1 | tail -3
pnpm build:lib:client 2>&1 | tail -3
pnpm build:web 2>&1 | tail -3
echo "done. Refresh the DSH Web GUI page once to pick up the new bundle."
echo "(Host-side settings changes register at the next dsh process restart.)"
