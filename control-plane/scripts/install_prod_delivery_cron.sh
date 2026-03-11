#!/usr/bin/env bash
set -euo pipefail

QUEUE_EXPR="${QUEUE_EXPR:-13,43 * * * *}"
HANDOFF_EXPR="${HANDOFF_EXPR:-15,45 * * * *}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QUEUE_LOCK="$HOME/openclaw/runtime/agentos/prod-delivery-queue.lock"
HANDOFF_LOCK="$HOME/openclaw/runtime/agentos/prod-delivery-handoff.lock"
QUEUE_LOG="$HOME/openclaw/logs/agentos-prod-delivery-queue.log"
HANDOFF_LOG="$HOME/openclaw/logs/agentos-prod-delivery-handoff.log"

mkdir -p "$(dirname "$QUEUE_LOCK")" "$(dirname "$QUEUE_LOG")"

current="$(crontab -l 2>/dev/null || true)"
current="$(printf '%s\n' "$current" | sed '/^# === OpenClaw Agent OS Prod delivery ===$/,/^# === \/OpenClaw Agent OS Prod delivery ===$/d')"
block=$(cat <<EOF
# === OpenClaw Agent OS Prod delivery ===
$QUEUE_EXPR flock -n $QUEUE_LOCK $ROOT_DIR/control-plane/scripts/prod_delivery_queue_cycle.sh >> $QUEUE_LOG 2>&1
$HANDOFF_EXPR flock -n $HANDOFF_LOCK $ROOT_DIR/control-plane/scripts/prod_delivery_handoff_cycle.sh >> $HANDOFF_LOG 2>&1
# === /OpenClaw Agent OS Prod delivery ===
EOF
)
printf '%s\n%s\n' "$current" "$block" | crontab -
echo "[prod-delivery-cron] installed"
