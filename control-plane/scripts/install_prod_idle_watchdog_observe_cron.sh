#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_RUNTIME_DIR="${PROD_RUNTIME_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos}"
PROD_LOG_DIR="${PROD_LOG_DIR:-$PROD_OPENCLAW_HOME/logs}"
PROD_IDLE_WATCHDOG_SCHEDULE="${PROD_IDLE_WATCHDOG_SCHEDULE:-7 * * * *}"
PROD_IDLE_WATCHDOG_LOCK="${PROD_IDLE_WATCHDOG_LOCK:-$PROD_RUNTIME_DIR/prod-idle-watchdog-observe.lock}"

mkdir -p "$PROD_RUNTIME_DIR" "$PROD_LOG_DIR"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Prod idle watchdog observe ===$/,/^# === \/OpenClaw Agent OS Prod idle watchdog observe ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Prod idle watchdog observe ===
$PROD_IDLE_WATCHDOG_SCHEDULE flock -n $PROD_IDLE_WATCHDOG_LOCK $ROOT_DIR/control-plane/scripts/prod_idle_watchdog_observe_cycle.sh >> $PROD_LOG_DIR/agentos-prod-idle-watchdog-observe.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog observe ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed Agent OS Prod idle watchdog observe cron block."
echo "Log file: $PROD_LOG_DIR/agentos-prod-idle-watchdog-observe.log"
echo "Schedule: $PROD_IDLE_WATCHDOG_SCHEDULE"
