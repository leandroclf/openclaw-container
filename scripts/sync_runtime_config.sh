#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
SOURCE_CONFIG="${SOURCE_CONFIG:-$OPENCLAW_HOME/data/openclaw.json}"
RUNTIME_DIR="${RUNTIME_DIR:-$OPENCLAW_HOME/runtime}"
RUNTIME_CONFIG_DIR="${RUNTIME_CONFIG_DIR:-$RUNTIME_DIR/config}"

if [ ! -f "$SOURCE_CONFIG" ]; then
  echo "ERROR: source config not found at $SOURCE_CONFIG" >&2
  exit 1
fi

mkdir -p "$RUNTIME_DIR" "$RUNTIME_CONFIG_DIR"
cp "$SOURCE_CONFIG" "$RUNTIME_DIR/openclaw.json"
cp "$SOURCE_CONFIG" "$RUNTIME_CONFIG_DIR/openclaw.json"
chmod 600 "$RUNTIME_DIR/openclaw.json" "$RUNTIME_CONFIG_DIR/openclaw.json"

echo "Runtime config synchronized from $SOURCE_CONFIG"
