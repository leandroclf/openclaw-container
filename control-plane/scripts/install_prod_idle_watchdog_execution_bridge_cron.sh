#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_RUNTIME_DIR="${PROD_RUNTIME_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos}"
PROD_LOG_DIR="${PROD_LOG_DIR:-$PROD_OPENCLAW_HOME/logs}"
PROD_IDLE_WATCHDOG_EXECUTION_SCHEDULE="${PROD_IDLE_WATCHDOG_EXECUTION_SCHEDULE:-12 * * * *}"
PROD_IDLE_WATCHDOG_EXECUTION_LOCK="${PROD_IDLE_WATCHDOG_EXECUTION_LOCK:-$PROD_RUNTIME_DIR/prod-idle-watchdog-execution.lock}"
EXECUTION_BRIDGE_MODE="${EXECUTION_BRIDGE_MODE:-dry-run}"
INTERNAL_WATCHDOG_PRIMARY="${INTERNAL_WATCHDOG_PRIMARY:-true}"
TARGET_CRON_NAME="${TARGET_CRON_NAME:-Autopilot sequential delivery cycle}"

mkdir -p "$PROD_RUNTIME_DIR" "$PROD_LOG_DIR"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Prod idle watchdog execution bridge ===$/,/^# === \/OpenClaw Agent OS Prod idle watchdog execution bridge ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Prod idle watchdog execution bridge ===
$PROD_IDLE_WATCHDOG_EXECUTION_SCHEDULE flock -n $PROD_IDLE_WATCHDOG_EXECUTION_LOCK env EXECUTION_BRIDGE_MODE=$EXECUTION_BRIDGE_MODE INTERNAL_WATCHDOG_PRIMARY=$INTERNAL_WATCHDOG_PRIMARY TARGET_CRON_NAME=$(printf '%q' "$TARGET_CRON_NAME") $ROOT_DIR/control-plane/scripts/prod_idle_watchdog_execution_bridge_cycle.sh >> $PROD_LOG_DIR/agentos-prod-idle-watchdog-execution.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog execution bridge ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed Agent OS Prod idle watchdog execution bridge cron block."
echo "Log file: $PROD_LOG_DIR/agentos-prod-idle-watchdog-execution.log"
echo "Schedule: $PROD_IDLE_WATCHDOG_EXECUTION_SCHEDULE"
