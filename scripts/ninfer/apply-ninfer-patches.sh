#!/usr/bin/env bash
# Apply the local NInfer patches to the NInfer checkout. Idempotent.
#
# Kit layout (vault scripts/ninfer/ or ~/.dsh/ninfer/): this script's kit
# directory contains patches/ and fixtures/; the script itself may live
# anywhere (live location: ~/.dsh/bin/apply-ninfer-patches.sh).
#
# Usage: apply-ninfer-patches.sh [--install]
#   --install  sync patches + fixtures into ~/.dsh/ninfer/ and this script
#              into ~/.dsh/bin/ (then exit; run again without the flag to
#              apply).
set -euo pipefail

KIT_DIR=""
for d in "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" "$HOME/.dsh/ninfer"; do
  if [ -d "$d/patches" ]; then KIT_DIR="$d"; break; fi
done
if [ -z "$KIT_DIR" ]; then
  echo "apply-ninfer-patches: no kit found (patches/ dir next to script or in ~/.dsh/ninfer)" >&2
  exit 2
fi

NINFER_DIR="${NINFER_DIR:-/home/oem/Apps/ninfer}"

if [ "${1:-}" = "--install" ]; then
  mkdir -p "$HOME/.dsh/ninfer/patches" "$HOME/.dsh/ninfer/fixtures" "$HOME/.dsh/bin"
  cp -f "$KIT_DIR"/patches/*.patch "$HOME/.dsh/ninfer/patches/"
  cp -f "$KIT_DIR"/fixtures/* "$HOME/.dsh/ninfer/fixtures/"
  cp -f "${BASH_SOURCE[0]}" "$HOME/.dsh/bin/apply-ninfer-patches.sh"
  chmod +x "$HOME/.dsh/bin/apply-ninfer-patches.sh"
  echo "installed kit into ~/.dsh/ninfer + ~/.dsh/bin (run again without --install to apply)"
  exit 0
fi

if [ ! -d "$NINFER_DIR/.git" ]; then
  echo "apply-ninfer-patches: NInfer checkout not found at $NINFER_DIR" >&2
  exit 2
fi

status=0
for patch in "$KIT_DIR"/patches/*.patch; do
  [ -e "$patch" ] || continue
  name="$(basename "$patch")"
  if git -C "$NINFER_DIR" apply -R --check "$patch" 2>/dev/null; then
    echo "skip  $name (already applied)"
  elif git -C "$NINFER_DIR" apply --check "$patch" 2>/dev/null; then
    git -C "$NINFER_DIR" apply "$patch"
    echo "apply $name (clean)"
  elif git -C "$NINFER_DIR" apply --3way --check "$patch" 2>/dev/null; then
    git -C "$NINFER_DIR" apply --3way "$patch"
    echo "apply $name (3-way merge)"
  else
    echo "CONFLICT $name — resolve by hand (see scripts/ninfer/README.md), then re-run." >&2
    status=1
  fi
done
if [ "$status" -ne 0 ]; then
  echo "apply-ninfer-patches: NOT rebuilt (conflict)." >&2
  exit 1
fi

# Install regression fixtures (idempotent; never overwrites an existing file).
for fx in "$KIT_DIR"/fixtures/*; do
  [ -e "$fx" ] || continue
  target="$NINFER_DIR/tests/fixtures/media/$(basename "$fx")"
  if [ -f "$target" ]; then
    echo "skip  fixture $(basename "$fx") (present)"
  else
    mkdir -p "$(dirname "$target")"
    cp -f "$fx" "$target"
    echo "install fixture $(basename "$fx")"
  fi
done

# Rebuild tail (only when a build dir exists; the applier never configures one).
if [ -d "$NINFER_DIR/build" ]; then
  echo "rebuild (ninja) + run media decode test…"
  (cd "$NINFER_DIR/build" && ninja ninfer_media_decode_test apps/ninfer-serve \
     && ./tests/ninfer_media_decode_test)
  echo "apply-ninfer-patches: done. Restart the server via ./start.sh (user-managed)."
else
  echo "apply-ninfer-patches: no build/ dir — applied, not rebuilt."
fi
