#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
CANONICAL_DIR="$OPENCLAW_HOME/data/finance"
CANONICAL_FILE="$CANONICAL_DIR/ledger.csv"
SOURCE="${1:-${OPENCLAW_LEDGER_SOURCE_PATH:-}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ -z "${SOURCE:-}" ]; then
  SUGGESTED_SOURCE="$("$PYTHON_BIN" - "$ROOT_DIR" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))

from scripts.finance_export_discovery import discover_finance_exports

report = discover_finance_exports()
candidate = report.get("recommendedSource") or {}
print(candidate.get("path", ""))
PY
)"
  cat >&2 <<'EOF'
Usage:
  install_finance_export_dropin.sh /path/to/real-ledger-export.csv

Or set:
  OPENCLAW_LEDGER_SOURCE_PATH=/path/to/real-ledger-export.csv
EOF
  if [ -n "${SUGGESTED_SOURCE:-}" ]; then
    echo "Suggested finance export source: ${SUGGESTED_SOURCE}" >&2
  fi
  exit 1
fi

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: source export not found: $SOURCE" >&2
  exit 1
fi

mkdir -p "$CANONICAL_DIR"
chmod 700 "$CANONICAL_DIR"

SOURCE_REAL="$(python3 - "$SOURCE" "$CANONICAL_FILE" <<'PY'
import sys
from pathlib import Path

source = Path(sys.argv[1]).expanduser().resolve(strict=False)
target = Path(sys.argv[2]).expanduser().resolve(strict=False)
print("same" if source == target else "different")
PY
)"

if [ "$SOURCE_REAL" = "same" ]; then
  echo "Canonical finance export already points to: $SOURCE"
else
  SOURCE_SUFFIX="${SOURCE##*.}"
  SOURCE_SUFFIX=".${SOURCE_SUFFIX,,}"
  case "$SOURCE_SUFFIX" in
    .xlsx|.xlsm)
      python3 "$ROOT_DIR/scripts/finance_xlsx_to_csv.py" "$SOURCE" "$CANONICAL_FILE"
      echo "Converted XLSX finance export to canonical CSV: $CANONICAL_FILE"
      ;;
    *)
      if ln -sfn "$SOURCE" "$CANONICAL_FILE" 2>/dev/null; then
        echo "Linked canonical finance export to: $SOURCE"
      else
        cp -f "$SOURCE" "$CANONICAL_FILE"
        echo "Copied canonical finance export to: $CANONICAL_FILE"
      fi
      ;;
  esac
fi

if [ -x "$ROOT_DIR/scripts/ledger_export_watchdog.py" ]; then
  python3 "$ROOT_DIR/scripts/ledger_export_watchdog.py" >/dev/null
fi
