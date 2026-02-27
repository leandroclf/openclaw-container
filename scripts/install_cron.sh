#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
ALERTS_FILE="${ALERTS_FILE:-$OPENCLAW_HOME/config/alerts.env}"

HEALTH_SCHEDULE="${HEALTH_SCHEDULE:-*/15 * * * *}"
BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-0 3 * * 0}"
UPDATE_SCHEDULE="${UPDATE_SCHEDULE:-30 3 * * *}"
MODEL_ROUTER_SCHEDULE="${MODEL_ROUTER_SCHEDULE:-45 3 * * *}"
MODEL_ROUTER_OBJECTIVE="${MODEL_ROUTER_OBJECTIVE:-balanced_default}"
PRUNE_LOGS_SCHEDULE="${PRUNE_LOGS_SCHEDULE:-15 4 * * *}"

mkdir -p "$OPENCLAW_HOME/config" "$OPENCLAW_HOME/logs"

if [ ! -f "$ALERTS_FILE" ]; then
  cat > "$ALERTS_FILE" <<'EOF'
# OpenClaw notification target (Telegram user_id or chat_id)
ALERT_TELEGRAM_TARGET=
EOF
fi
chmod 600 "$ALERTS_FILE"

tmp="$(mktemp)"
if ! crontab -l > "$tmp" 2>/dev/null; then
  : > "$tmp"
fi

sed -i '/^# === OpenClaw container ops ===$/,/^# === \/OpenClaw container ops ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw container ops ===
$HEALTH_SCHEDULE . $ALERTS_FILE && $ROOT_DIR/scripts/healthcheck_notify.sh >> $OPENCLAW_HOME/logs/healthcheck.log 2>&1
$BACKUP_SCHEDULE $ROOT_DIR/scripts/backup.sh >> $OPENCLAW_HOME/logs/backup.log 2>&1
$UPDATE_SCHEDULE $ROOT_DIR/scripts/update.sh >> $OPENCLAW_HOME/logs/update.log 2>&1
$MODEL_ROUTER_SCHEDULE $ROOT_DIR/scripts/model_router.py --objective $MODEL_ROUTER_OBJECTIVE --probe --apply >> $OPENCLAW_HOME/logs/model-router.log 2>&1
$PRUNE_LOGS_SCHEDULE $ROOT_DIR/scripts/prune_logs.sh >> $OPENCLAW_HOME/logs/prune.log 2>&1
# === /OpenClaw container ops ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed OpenClaw cron block."
echo "Edit alert target in: $ALERTS_FILE"
echo "Test now:"
echo "  . $ALERTS_FILE && $ROOT_DIR/scripts/healthcheck_notify.sh"
