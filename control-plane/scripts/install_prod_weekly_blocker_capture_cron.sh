#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/openclaw-workspace}"
PROD_AGENTOS_DB="${PROD_AGENTOS_DB:-$HOME/openclaw/runtime/agentos/prod-observe.db}"
PROD_WEEKLY_CAPTURE_SCHEDULE="${PROD_WEEKLY_CAPTURE_SCHEDULE:-15 7 * * 0}"
PROD_WEEKLY_CAPTURE_LOCK="${PROD_WEEKLY_CAPTURE_LOCK:-$HOME/openclaw/runtime/agentos/prod-weekly-blocker-capture.lock}"
PROD_WEEKLY_CAPTURE_LOG="${PROD_WEEKLY_CAPTURE_LOG:-$HOME/openclaw/logs/agentos-prod-weekly-blocker-capture.log}"

mkdir -p "$(dirname "$PROD_WEEKLY_CAPTURE_LOCK")" "$(dirname "$PROD_WEEKLY_CAPTURE_LOG")"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Weekly finance\/legal capture ===$/,/^# === \/OpenClaw Agent OS Weekly finance\/legal capture ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Weekly finance/legal capture ===
$PROD_WEEKLY_CAPTURE_SCHEDULE flock -n $PROD_WEEKLY_CAPTURE_LOCK $ROOT_DIR/control-plane/scripts/run_workflow.sh --db $PROD_AGENTOS_DB --name weekly_blocker_capture --workspace-root $PROD_WORKSPACE_ROOT >> $PROD_WEEKLY_CAPTURE_LOG 2>&1
# === /OpenClaw Agent OS Weekly finance/legal capture ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed OpenClaw Agent OS weekly finance/legal capture cron block."
echo "Schedule: $PROD_WEEKLY_CAPTURE_SCHEDULE"
echo "Log file: $PROD_WEEKLY_CAPTURE_LOG"
