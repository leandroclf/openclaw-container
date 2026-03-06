#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_RUNTIME_DIR="${PROD_RUNTIME_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos}"
PROD_LOG_DIR="${PROD_LOG_DIR:-$PROD_OPENCLAW_HOME/logs}"
PROD_POLICY_AUDIT_SCHEDULE="${PROD_POLICY_AUDIT_SCHEDULE:-19,49 * * * *}"
PROD_POLICY_AUDIT_LOCK="${PROD_POLICY_AUDIT_LOCK:-$PROD_RUNTIME_DIR/prod-policy-audit.lock}"

mkdir -p "$PROD_RUNTIME_DIR" "$PROD_LOG_DIR"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Prod policy audit ===$/,/^# === \/OpenClaw Agent OS Prod policy audit ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Prod policy audit ===
$PROD_POLICY_AUDIT_SCHEDULE flock -n $PROD_POLICY_AUDIT_LOCK $ROOT_DIR/control-plane/scripts/prod_policy_audit_cycle.sh >> $PROD_LOG_DIR/agentos-prod-policy-audit.log 2>&1
# === /OpenClaw Agent OS Prod policy audit ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed Agent OS Prod policy audit cron block."
echo "Log file: $PROD_LOG_DIR/agentos-prod-policy-audit.log"
echo "Schedule: $PROD_POLICY_AUDIT_SCHEDULE"
