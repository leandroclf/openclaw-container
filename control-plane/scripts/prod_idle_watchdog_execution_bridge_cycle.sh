#!/usr/bin/env bash
set -euo pipefail

PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
BRIDGE_DIR="${BRIDGE_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"
PROFILE="${PROFILE:-prod}"
EXECUTION_BRIDGE_MODE="${EXECUTION_BRIDGE_MODE:-dry-run}"
INTERNAL_WATCHDOG_PRIMARY="${INTERNAL_WATCHDOG_PRIMARY:-true}"
TARGET_CRON_NAME="${TARGET_CRON_NAME:-Autopilot sequential delivery cycle}"

docker exec openclaw openclaw --profile "$PROFILE" gateway health >/dev/null

args=(
  --bridge-dir "$BRIDGE_DIR"
  --profile "$PROFILE"
  --internal-watchdog-primary "$INTERNAL_WATCHDOG_PRIMARY"
)

if [ "$EXECUTION_BRIDGE_MODE" = "activate" ]; then
  args+=(--activate --trigger-cron-name "$TARGET_CRON_NAME")
fi

python3 /home/leandro/openclaw-container/scripts/idle_watchdog_execution_bridge.py "${args[@]}"

docker exec openclaw openclaw --profile "$PROFILE" gateway health >/dev/null
