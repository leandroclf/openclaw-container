#!/usr/bin/env bash
set -euo pipefail

PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
BRIDGE_DIR="${BRIDGE_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "${1:-}" != "--confirm-cutover" ]]; then
  echo "Refusing to activate without --confirm-cutover."
  exit 2
fi

docker context ls >/dev/null
docker context show >/dev/null
docker exec openclaw openclaw --profile prod gateway health >/dev/null

readiness_output="$(python3 "$ROOT_DIR/scripts/idle_watchdog_cutover_readiness.py" --bridge-dir "$BRIDGE_DIR")"
printf '%s\n' "$readiness_output"

if ! grep -q '^\[GO\]' <<<"$readiness_output"; then
  echo "Cutover activation blocked by readiness gate."
  exit 3
fi

python3 "$ROOT_DIR/scripts/idle_watchdog_execution_bridge.py" \
  --bridge-dir "$BRIDGE_DIR" \
  --activate \
  --internal-watchdog-primary false

docker exec openclaw openclaw --profile prod gateway health >/dev/null

echo "Idle watchdog execution bridge activated."
