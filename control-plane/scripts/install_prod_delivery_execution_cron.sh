#!/usr/bin/env bash
set -euo pipefail

CONSUMER_EXPR="${CONSUMER_EXPR:-17,47 * * * *}"
EXECUTION_EXPR="${EXECUTION_EXPR:-19,49 * * * *}"
EXECUTION_BRIDGE_MODE="${EXECUTION_BRIDGE_MODE:-dry-run}"
EXECUTION_BACKEND="${EXECUTION_BACKEND:-agent}"
TRIGGER_AGENT="${TRIGGER_AGENT:-main}"
INTERNAL_DELIVERY_PRIMARY="${INTERNAL_DELIVERY_PRIMARY:-true}"
ALLOW_DISABLED_CRON="${ALLOW_DISABLED_CRON:-false}"
TARGET_CRON_NAME="${TARGET_CRON_NAME:-Autopilot sequential delivery cycle}"
TARGET_CRON_ID="${TARGET_CRON_ID:-e6d5079d-3eaa-46fa-ac4a-4f77add89b18}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONSUMER_LOCK="$HOME/openclaw/runtime/agentos/prod-delivery-consumer.lock"
EXECUTION_LOCK="$HOME/openclaw/runtime/agentos/prod-delivery-execution.lock"
CONSUMER_LOG="$HOME/openclaw/logs/agentos-prod-delivery-consumer.log"
EXECUTION_LOG="$HOME/openclaw/logs/agentos-prod-delivery-execution.log"

mkdir -p "$(dirname "$CONSUMER_LOCK")" "$(dirname "$CONSUMER_LOG")"

current="$(crontab -l 2>/dev/null || true)"
current="$(printf '%s\n' "$current" | awk '
  /^# === OpenClaw Agent OS Prod delivery execution ===$/ {skip=1; next}
  /^# === \/OpenClaw Agent OS Prod delivery execution ===$/ {skip=0; next}
  skip != 1 {print}
')"
block=$(cat <<EOF
# === OpenClaw Agent OS Prod delivery execution ===
$CONSUMER_EXPR flock -n $CONSUMER_LOCK $ROOT_DIR/control-plane/scripts/prod_delivery_handoff_consumer_cycle.sh >> $CONSUMER_LOG 2>&1
$EXECUTION_EXPR flock -n $EXECUTION_LOCK env EXECUTION_BRIDGE_MODE=$EXECUTION_BRIDGE_MODE EXECUTION_BACKEND=$EXECUTION_BACKEND TRIGGER_AGENT=$TRIGGER_AGENT INTERNAL_DELIVERY_PRIMARY=$INTERNAL_DELIVERY_PRIMARY ALLOW_DISABLED_CRON=$ALLOW_DISABLED_CRON TARGET_CRON_NAME='$TARGET_CRON_NAME' TARGET_CRON_ID='$TARGET_CRON_ID' $ROOT_DIR/control-plane/scripts/prod_delivery_execution_bridge_cycle.sh >> $EXECUTION_LOG 2>&1
# === /OpenClaw Agent OS Prod delivery execution ===
EOF
)
printf '%s\n%s\n' "$current" "$block" | crontab -
echo "[prod-delivery-execution-cron] installed"
