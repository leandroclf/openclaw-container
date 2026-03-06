#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_RUNTIME_DIR="${PROD_RUNTIME_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos}"
PROD_LOG_DIR="${PROD_LOG_DIR:-$PROD_OPENCLAW_HOME/logs}"
PROD_OBSERVE_SCHEDULE="${PROD_OBSERVE_SCHEDULE:-17,47 * * * *}"
PROD_OBSERVE_LOCK="${PROD_OBSERVE_LOCK:-$PROD_RUNTIME_DIR/prod-observe.lock}"

mkdir -p "$PROD_RUNTIME_DIR" "$PROD_LOG_DIR"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Prod observe ===$/,/^# === \/OpenClaw Agent OS Prod observe ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Prod observe ===
$PROD_OBSERVE_SCHEDULE flock -n $PROD_OBSERVE_LOCK $ROOT_DIR/control-plane/scripts/prod_observe_cycle.sh >> $PROD_LOG_DIR/agentos-prod-observe.log 2>&1
# === /OpenClaw Agent OS Prod observe ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed Agent OS Prod observe cron block."
echo "Log file: $PROD_LOG_DIR/agentos-prod-observe.log"
echo "Schedule: $PROD_OBSERVE_SCHEDULE"
