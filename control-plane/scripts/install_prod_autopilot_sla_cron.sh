#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_RUNTIME_DIR="${PROD_RUNTIME_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos}"
PROD_LOG_DIR="${PROD_LOG_DIR:-$PROD_OPENCLAW_HOME/logs}"
PROD_AUTOPILOT_SLA_SCHEDULE="${PROD_AUTOPILOT_SLA_SCHEDULE:-45 22 * * *}"
PROD_AUTOPILOT_SLA_LOCK="${PROD_AUTOPILOT_SLA_LOCK:-$PROD_RUNTIME_DIR/prod-autopilot-sla.lock}"

mkdir -p "$PROD_RUNTIME_DIR" "$PROD_LOG_DIR"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Prod autopilot SLA ===$/,/^# === \/OpenClaw Agent OS Prod autopilot SLA ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Prod autopilot SLA ===
$PROD_AUTOPILOT_SLA_SCHEDULE flock -n $PROD_AUTOPILOT_SLA_LOCK $ROOT_DIR/control-plane/scripts/prod_autopilot_sla_cycle.sh >> $PROD_LOG_DIR/agentos-prod-autopilot-sla.log 2>&1
# === /OpenClaw Agent OS Prod autopilot SLA ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed Agent OS Prod autopilot SLA cron block."
echo "Log file: $PROD_LOG_DIR/agentos-prod-autopilot-sla.log"
echo "Schedule: $PROD_AUTOPILOT_SLA_SCHEDULE"
