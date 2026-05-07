#!/usr/bin/env bash
set -euo pipefail

PET_ID="haengseongi"
DISPLAY_NAME="행성이"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME="${CODEX_HOME:-"$HOME/.codex"}"
SOURCE_DIR="$SCRIPT_DIR/pets/$PET_ID"
TARGET_DIR="$CODEX_HOME/pets/$PET_ID"

if [[ ! -f "$SOURCE_DIR/pet.json" || ! -f "$SOURCE_DIR/spritesheet.webp" ]]; then
  echo "Could not find pet package files in: $SOURCE_DIR" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
cp "$SOURCE_DIR/pet.json" "$TARGET_DIR/pet.json"
cp "$SOURCE_DIR/spritesheet.webp" "$TARGET_DIR/spritesheet.webp"

cat <<EOF
Installed $DISPLAY_NAME Codex pet.

Location:
  $TARGET_DIR

Next:
  1. Open Codex Desktop.
  2. Type /pet.
  3. Press Refresh.
  4. Select $DISPLAY_NAME.
EOF
