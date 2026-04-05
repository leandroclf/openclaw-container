#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
CANONICAL_DIR="$OPENCLAW_HOME/data/finance"
CANONICAL_FILE="$CANONICAL_DIR/ledger.csv"
SOURCE="${1:-${OPENCLAW_LEDGER_SOURCE_PATH:-}}"

if [ -z "${SOURCE:-}" ]; then
  cat >&2 <<'EOF'
Usage:
  install_finance_export_dropin.sh /path/to/real-ledger-export.csv

Or set:
  OPENCLAW_LEDGER_SOURCE_PATH=/path/to/real-ledger-export.csv
EOF
  exit 1
fi

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: source export not found: $SOURCE" >&2
  exit 1
fi

mkdir -p "$CANONICAL_DIR"
chmod 700 "$CANONICAL_DIR"

if ln -sfn "$SOURCE" "$CANONICAL_FILE" 2>/dev/null; then
  echo "Linked canonical finance export to: $SOURCE"
else
  cp -f "$SOURCE" "$CANONICAL_FILE"
  echo "Copied canonical finance export to: $CANONICAL_FILE"
fi

if [ -x "$ROOT_DIR/scripts/ledger_export_watchdog.py" ]; then
  python3 "$ROOT_DIR/scripts/ledger_export_watchdog.py" >/dev/null
fi
