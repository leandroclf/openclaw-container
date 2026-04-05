#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/openclaw-workspace}"
PROD_AGENTOS_DB="${PROD_AGENTOS_DB:-$HOME/openclaw/runtime/agentos/prod-observe.db}"
PROD_FINANCE_EXPORT_AUTOWIRE_SCHEDULE="${PROD_FINANCE_EXPORT_AUTOWIRE_SCHEDULE:-5,35 * * * *}"
PROD_FINANCE_EXPORT_AUTOWIRE_LOCK="${PROD_FINANCE_EXPORT_AUTOWIRE_LOCK:-$HOME/openclaw/runtime/agentos/prod-finance-export-autowire.lock}"
PROD_FINANCE_EXPORT_AUTOWIRE_LOG="${PROD_FINANCE_EXPORT_AUTOWIRE_LOG:-$HOME/openclaw/logs/agentos-prod-finance-export-autowire.log}"

mkdir -p "$(dirname "$PROD_FINANCE_EXPORT_AUTOWIRE_LOCK")" "$(dirname "$PROD_FINANCE_EXPORT_AUTOWIRE_LOG")"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Finance export autowire ===$/,/^# === \/OpenClaw Agent OS Finance export autowire ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Finance export autowire ===
$PROD_FINANCE_EXPORT_AUTOWIRE_SCHEDULE flock -n $PROD_FINANCE_EXPORT_AUTOWIRE_LOCK $ROOT_DIR/control-plane/scripts/run_workflow.sh --db $PROD_AGENTOS_DB --name finance_export_autowire --workspace-root $PROD_WORKSPACE_ROOT >> $PROD_FINANCE_EXPORT_AUTOWIRE_LOG 2>&1
# === /OpenClaw Agent OS Finance export autowire ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed OpenClaw Agent OS finance export autowire cron block."
echo "Schedule: $PROD_FINANCE_EXPORT_AUTOWIRE_SCHEDULE"
echo "Log file: $PROD_FINANCE_EXPORT_AUTOWIRE_LOG"
