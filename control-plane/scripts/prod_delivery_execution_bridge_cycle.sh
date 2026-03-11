#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_HANDOFF_DIR="${PROD_HANDOFF_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"
EXECUTION_BRIDGE_MODE="${EXECUTION_BRIDGE_MODE:-dry-run}"
INTERNAL_DELIVERY_PRIMARY="${INTERNAL_DELIVERY_PRIMARY:-true}"
TARGET_CRON_NAME="${TARGET_CRON_NAME:-Autopilot sequential delivery cycle}"
TARGET_CRON_ID="${TARGET_CRON_ID:-}"
TRIGGER_TIMEOUT_MS="${TRIGGER_TIMEOUT_MS:-900000}"
ALLOW_DISABLED_CRON="${ALLOW_DISABLED_CRON:-false}"

mkdir -p "$PROD_HANDOFF_DIR"

echo "[prod-delivery-execution] $(date -Iseconds) start"
echo "[prod-delivery-execution] handoffs=$PROD_HANDOFF_DIR"
echo "[prod-delivery-execution] mode=$EXECUTION_BRIDGE_MODE"
echo "[prod-delivery-execution] internal_primary=$INTERNAL_DELIVERY_PRIMARY"

docker exec "$PROD_CONTAINER_NAME" openclaw --profile prod gateway health

cmd=(
  python3 "$ROOT_DIR/scripts/delivery_execution_bridge.py"
  --bridge-dir "$PROD_HANDOFF_DIR"
  --profile prod
  --trigger-cron-name "$TARGET_CRON_NAME"
  --trigger-timeout-ms "$TRIGGER_TIMEOUT_MS"
  --internal-delivery-primary "$INTERNAL_DELIVERY_PRIMARY"
)
if [[ -n "$TARGET_CRON_ID" ]]; then
  cmd+=(--trigger-cron-id "$TARGET_CRON_ID")
fi
if [[ "$ALLOW_DISABLED_CRON" == "true" ]]; then
  cmd+=(--allow-disabled-cron)
fi
if [[ "$EXECUTION_BRIDGE_MODE" == "activate" ]]; then
  cmd+=(--activate)
fi
"${cmd[@]}"

docker exec "$PROD_CONTAINER_NAME" openclaw --profile prod gateway health

echo "[prod-delivery-execution] $(date -Iseconds) done"
