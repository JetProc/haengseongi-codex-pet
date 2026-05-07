#!/usr/bin/env bash
set -euo pipefail

PET_ID="haengseongi"
DISPLAY_NAME="행성이"
BASE_URL="${HAENGSEONGI_PET_BASE_URL:-https://raw.githubusercontent.com/JetProc/haengseongi-codex-pet/main}"

if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
  SCRIPT_DIR=""
fi
CODEX_HOME="${CODEX_HOME:-"$HOME/.codex"}"
SOURCE_DIR="$SCRIPT_DIR/pets/$PET_ID"
TARGET_DIR="$CODEX_HOME/pets/$PET_ID"

mkdir -p "$TARGET_DIR"

if [[ -f "$SOURCE_DIR/pet.json" && -f "$SOURCE_DIR/spritesheet.webp" ]]; then
  cp "$SOURCE_DIR/pet.json" "$TARGET_DIR/pet.json"
  cp "$SOURCE_DIR/spritesheet.webp" "$TARGET_DIR/spritesheet.webp"
else
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required when installing without a local repository checkout." >&2
    exit 1
  fi

  curl -fsSL "$BASE_URL/pets/$PET_ID/pet.json" -o "$TARGET_DIR/pet.json"
  curl -fsSL "$BASE_URL/pets/$PET_ID/spritesheet.webp" -o "$TARGET_DIR/spritesheet.webp"
fi

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
