#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
BRIDGE_DIR="${BRIDGE_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"
PROFILE="${PROFILE:-prod}"
EXECUTION_BRIDGE_MODE="${EXECUTION_BRIDGE_MODE:-dry-run}"
INTERNAL_WATCHDOG_PRIMARY="${INTERNAL_WATCHDOG_PRIMARY:-true}"
TARGET_CRON_NAME="${TARGET_CRON_NAME:-Autopilot sequential delivery cycle}"

docker_guard_ensure "prod-idle-watchdog-execution-bridge" || true
docker_guard_health_or_skip openclaw "$PROFILE" "prod-idle-watchdog-execution-bridge"

args=(
  --bridge-dir "$BRIDGE_DIR"
  --profile "$PROFILE"
  --internal-watchdog-primary "$INTERNAL_WATCHDOG_PRIMARY"
)

if [ "$EXECUTION_BRIDGE_MODE" = "activate" ]; then
  args+=(--activate --trigger-cron-name "$TARGET_CRON_NAME")
fi

python3 /home/leandro/openclaw-container/scripts/idle_watchdog_execution_bridge.py "${args[@]}"

docker_guard_health_or_skip openclaw "$PROFILE" "prod-idle-watchdog-execution-bridge"
