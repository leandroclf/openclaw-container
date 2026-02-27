#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WITH_INTEGRATION=0

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--with-integration]

Runs repository validation gates:
  - unit tests (always)
  - regression contract tests (always)
  - integration container tests (optional)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-integration)
      WITH_INTEGRATION=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

echo "[gate] unit tests"
python3 -m unittest discover -s "$ROOT_DIR/tests/unit" -p "test_*.py" -t "$ROOT_DIR"

echo "[gate] regression tests"
python3 -m unittest discover -s "$ROOT_DIR/tests/regression" -p "test_*.py" -t "$ROOT_DIR"

if [[ "$WITH_INTEGRATION" -eq 1 ]]; then
  echo "[gate] integration tests"
  python3 -m unittest discover -s "$ROOT_DIR/tests/integration" -p "test_*.py" -t "$ROOT_DIR"
else
  echo "[gate] integration tests skipped (use --with-integration)"
fi

echo "[gate] done"
