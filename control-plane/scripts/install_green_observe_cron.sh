#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GREEN_OPENCLAW_HOME="${GREEN_OPENCLAW_HOME:-$HOME/openclaw-next}"
GREEN_RUNTIME_DIR="${GREEN_RUNTIME_DIR:-$GREEN_OPENCLAW_HOME/runtime/agentos}"
GREEN_LOG_DIR="${GREEN_LOG_DIR:-$GREEN_OPENCLAW_HOME/logs}"
GREEN_OBSERVE_SCHEDULE="${GREEN_OBSERVE_SCHEDULE:-12,32,52 * * * *}"
GREEN_OBSERVE_LOCK="${GREEN_OBSERVE_LOCK:-$GREEN_RUNTIME_DIR/green-observe.lock}"

mkdir -p "$GREEN_RUNTIME_DIR" "$GREEN_LOG_DIR"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw Agent OS Green observe ===$/,/^# === \/OpenClaw Agent OS Green observe ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw Agent OS Green observe ===
$GREEN_OBSERVE_SCHEDULE flock -n $GREEN_OBSERVE_LOCK $ROOT_DIR/control-plane/scripts/green_observe_cycle.sh >> $GREEN_LOG_DIR/agentos-green-observe.log 2>&1
# === /OpenClaw Agent OS Green observe ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed Agent OS Green observe cron block."
echo "Log file: $GREEN_LOG_DIR/agentos-green-observe.log"
echo "Schedule: $GREEN_OBSERVE_SCHEDULE"
