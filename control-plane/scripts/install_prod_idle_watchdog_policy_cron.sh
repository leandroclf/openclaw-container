#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_RUNTIME_DIR="${PROD_RUNTIME_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos}"
PROD_LOG_DIR="${PROD_LOG_DIR:-$PROD_OPENCLAW_HOME/logs}"
PROD_IDLE_WATCHDOG_POLICY_SCHEDULE="${PROD_IDLE_WATCHDOG_POLICY_SCHEDULE:-9 * * * *}"
PROD_IDLE_WATCHDOG_POLICY_LOCK="${PROD_IDLE_WATCHDOG_POLICY_LOCK:-$PROD_RUNTIME_DIR/prod-idle-watchdog-policy.lock}"

mkdir -p "$PROD_RUNTIME_DIR" "$PROD_LOG_DIR"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Prod idle watchdog policy ===$/,/^# === \/OpenClaw Agent OS Prod idle watchdog policy ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Prod idle watchdog policy ===
$PROD_IDLE_WATCHDOG_POLICY_SCHEDULE flock -n $PROD_IDLE_WATCHDOG_POLICY_LOCK $ROOT_DIR/control-plane/scripts/prod_idle_watchdog_policy_cycle.sh >> $PROD_LOG_DIR/agentos-prod-idle-watchdog-policy.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog policy ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed Agent OS Prod idle watchdog policy cron block."
echo "Log file: $PROD_LOG_DIR/agentos-prod-idle-watchdog-policy.log"
echo "Schedule: $PROD_IDLE_WATCHDOG_POLICY_SCHEDULE"
