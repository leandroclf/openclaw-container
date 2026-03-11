#!/usr/bin/env bash
set -euo pipefail

RECONCILE_EXPR="${RECONCILE_EXPR:-21,51 * * * *}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RECONCILE_LOCK="$HOME/openclaw/runtime/agentos/prod-delivery-reconcile.lock"
RECONCILE_LOG="$HOME/openclaw/logs/agentos-prod-delivery-reconcile.log"

mkdir -p "$(dirname "$RECONCILE_LOCK")" "$(dirname "$RECONCILE_LOG")"

current="$(crontab -l 2>/dev/null || true)"
current="$(printf '%s\n' "$current" | awk '
  /^# === OpenClaw Agent OS Prod delivery reconcile ===$/ {skip=1; next}
  /^# === \/OpenClaw Agent OS Prod delivery reconcile ===$/ {skip=0; next}
  skip != 1 {print}
')"
block=$(cat <<EOF
# === OpenClaw Agent OS Prod delivery reconcile ===
$RECONCILE_EXPR flock -n $RECONCILE_LOCK $ROOT_DIR/control-plane/scripts/prod_delivery_reconcile_cycle.sh >> $RECONCILE_LOG 2>&1
# === /OpenClaw Agent OS Prod delivery reconcile ===
EOF
)
printf '%s\n%s\n' "$current" "$block" | crontab -
echo "[prod-delivery-reconcile-cron] installed"
