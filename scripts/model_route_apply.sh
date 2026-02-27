#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: $0 <objective>"
  echo "Example: $0 balanced_default"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBJECTIVE="$1"

"$ROOT_DIR/scripts/model_router.py" --objective "$OBJECTIVE" --probe --apply --run-callbacks
