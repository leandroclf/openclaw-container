#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
ALERTS_FILE="${ALERTS_FILE:-$OPENCLAW_HOME/config/alerts.env}"

HEALTH_SCHEDULE="${HEALTH_SCHEDULE:-*/15 * * * *}"
DAILY_MAINTENANCE_SCHEDULE="${DAILY_MAINTENANCE_SCHEDULE:-10 6 * * *}"
BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-0 3 * * 0}"
UPDATE_SCHEDULE="${UPDATE_SCHEDULE:-30 3 * * *}"
MODEL_ROUTER_BASELINE_SCHEDULE="${MODEL_ROUTER_BASELINE_SCHEDULE:-45 3 * * *}"
MODEL_ROUTER_BASELINE_OBJECTIVE="${MODEL_ROUTER_BASELINE_OBJECTIVE:-cost_optimized}"
MODEL_ROUTER_BUSINESS_SCHEDULE="${MODEL_ROUTER_BUSINESS_SCHEDULE:-5 8 * * 1-5}"
MODEL_ROUTER_BUSINESS_OBJECTIVE="${MODEL_ROUTER_BUSINESS_OBJECTIVE:-balanced_default}"
MODEL_ROUTER_OFFHOURS_SCHEDULE="${MODEL_ROUTER_OFFHOURS_SCHEDULE:-5 20 * * *}"
MODEL_ROUTER_OFFHOURS_OBJECTIVE="${MODEL_ROUTER_OFFHOURS_OBJECTIVE:-cost_optimized}"
PRUNE_LOGS_SCHEDULE="${PRUNE_LOGS_SCHEDULE:-15 4 * * *}"
PROD_OBSERVE_SCHEDULE="${PROD_OBSERVE_SCHEDULE:-17,47 * * * *}"
PROD_POLICY_AUDIT_SCHEDULE="${PROD_POLICY_AUDIT_SCHEDULE:-19,49 * * * *}"
PROD_AUTOPILOT_SLA_SCHEDULE="${PROD_AUTOPILOT_SLA_SCHEDULE:-45 22 * * *}"
PROD_IDLE_WATCHDOG_OBSERVE_SCHEDULE="${PROD_IDLE_WATCHDOG_OBSERVE_SCHEDULE:-7 * * * *}"
PROD_IDLE_WATCHDOG_POLICY_SCHEDULE="${PROD_IDLE_WATCHDOG_POLICY_SCHEDULE:-9 * * * *}"
PROD_IDLE_WATCHDOG_HANDOFF_SCHEDULE="${PROD_IDLE_WATCHDOG_HANDOFF_SCHEDULE:-10 * * * *}"
PROD_IDLE_WATCHDOG_CONSUMER_SCHEDULE="${PROD_IDLE_WATCHDOG_CONSUMER_SCHEDULE:-11 * * * *}"
PROD_IDLE_WATCHDOG_EXECUTION_SCHEDULE="${PROD_IDLE_WATCHDOG_EXECUTION_SCHEDULE:-12 * * * *}"
PROD_DELIVERY_QUEUE_SCHEDULE="${PROD_DELIVERY_QUEUE_SCHEDULE:-13,43 * * * *}"
PROD_DELIVERY_HANDOFF_SCHEDULE="${PROD_DELIVERY_HANDOFF_SCHEDULE:-15,45 * * * *}"
PROD_DELIVERY_CONSUMER_SCHEDULE="${PROD_DELIVERY_CONSUMER_SCHEDULE:-17,47 * * * *}"
PROD_DELIVERY_EXECUTION_SCHEDULE="${PROD_DELIVERY_EXECUTION_SCHEDULE:-19,49 * * * *}"
PROD_DELIVERY_RECONCILE_SCHEDULE="${PROD_DELIVERY_RECONCILE_SCHEDULE:-21,51 * * * *}"
SEQUENTIAL_DELIVERY_CRON_ID="${SEQUENTIAL_DELIVERY_CRON_ID:-e6d5079d-3eaa-46fa-ac4a-4f77add89b18}"

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
sed -i '/^# === OpenClaw Agent OS Prod observe ===$/,/^# === \/OpenClaw Agent OS Prod observe ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod policy audit ===$/,/^# === \/OpenClaw Agent OS Prod policy audit ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod autopilot SLA ===$/,/^# === \/OpenClaw Agent OS Prod autopilot SLA ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod idle watchdog observe ===$/,/^# === \/OpenClaw Agent OS Prod idle watchdog observe ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod idle watchdog policy ===$/,/^# === \/OpenClaw Agent OS Prod idle watchdog policy ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod idle watchdog handoff bridge ===$/,/^# === \/OpenClaw Agent OS Prod idle watchdog handoff bridge ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod idle watchdog handoff consumer ===$/,/^# === \/OpenClaw Agent OS Prod idle watchdog handoff consumer ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod idle watchdog execution bridge ===$/,/^# === \/OpenClaw Agent OS Prod idle watchdog execution bridge ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod delivery ===$/,/^# === \/OpenClaw Agent OS Prod delivery ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod delivery execution ===$/,/^# === \/OpenClaw Agent OS Prod delivery execution ===$/d' "$tmp"
sed -i '/^# === OpenClaw Agent OS Prod delivery reconcile ===$/,/^# === \/OpenClaw Agent OS Prod delivery reconcile ===$/d' "$tmp"

cat >> "$tmp" <<EOF
# === OpenClaw container ops ===
$HEALTH_SCHEDULE . $ALERTS_FILE && $ROOT_DIR/scripts/healthcheck_notify.sh >> $OPENCLAW_HOME/logs/healthcheck.log 2>&1
$DAILY_MAINTENANCE_SCHEDULE . $ALERTS_FILE && $ROOT_DIR/scripts/daily_maintenance.sh >> $OPENCLAW_HOME/logs/daily-maintenance.log 2>&1
$BACKUP_SCHEDULE $ROOT_DIR/scripts/backup.sh >> $OPENCLAW_HOME/logs/backup.log 2>&1
$UPDATE_SCHEDULE $ROOT_DIR/scripts/update.sh >> $OPENCLAW_HOME/logs/update.log 2>&1
$MODEL_ROUTER_BASELINE_SCHEDULE $ROOT_DIR/scripts/model_router.py --objective $MODEL_ROUTER_BASELINE_OBJECTIVE --probe --apply >> $OPENCLAW_HOME/logs/model-router.log 2>&1
$MODEL_ROUTER_BUSINESS_SCHEDULE $ROOT_DIR/scripts/model_router.py --objective $MODEL_ROUTER_BUSINESS_OBJECTIVE --probe --apply >> $OPENCLAW_HOME/logs/model-router.log 2>&1
$MODEL_ROUTER_OFFHOURS_SCHEDULE $ROOT_DIR/scripts/model_router.py --objective $MODEL_ROUTER_OFFHOURS_OBJECTIVE --probe --apply >> $OPENCLAW_HOME/logs/model-router.log 2>&1
$PRUNE_LOGS_SCHEDULE $ROOT_DIR/scripts/prune_logs.sh >> $OPENCLAW_HOME/logs/prune.log 2>&1
# === /OpenClaw container ops ===
# === OpenClaw Agent OS Prod observe ===
$PROD_OBSERVE_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-observe.lock $ROOT_DIR/control-plane/scripts/prod_observe_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-observe.log 2>&1
# === /OpenClaw Agent OS Prod observe ===
# === OpenClaw Agent OS Prod policy audit ===
$PROD_POLICY_AUDIT_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-policy-audit.lock $ROOT_DIR/control-plane/scripts/prod_policy_audit_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-policy-audit.log 2>&1
# === /OpenClaw Agent OS Prod policy audit ===
# === OpenClaw Agent OS Prod autopilot SLA ===
$PROD_AUTOPILOT_SLA_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-autopilot-sla.lock $ROOT_DIR/control-plane/scripts/prod_autopilot_sla_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-autopilot-sla.log 2>&1
# === /OpenClaw Agent OS Prod autopilot SLA ===
# === OpenClaw Agent OS Prod idle watchdog observe ===
$PROD_IDLE_WATCHDOG_OBSERVE_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-idle-watchdog-observe.lock $ROOT_DIR/control-plane/scripts/prod_idle_watchdog_observe_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-idle-watchdog-observe.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog observe ===
# === OpenClaw Agent OS Prod idle watchdog policy ===
$PROD_IDLE_WATCHDOG_POLICY_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-idle-watchdog-policy.lock $ROOT_DIR/control-plane/scripts/prod_idle_watchdog_policy_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-idle-watchdog-policy.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog policy ===
# === OpenClaw Agent OS Prod idle watchdog handoff bridge ===
$PROD_IDLE_WATCHDOG_HANDOFF_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-idle-watchdog-handoff.lock $ROOT_DIR/control-plane/scripts/prod_idle_watchdog_handoff_bridge_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-idle-watchdog-handoff.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog handoff bridge ===
# === OpenClaw Agent OS Prod idle watchdog handoff consumer ===
$PROD_IDLE_WATCHDOG_CONSUMER_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-idle-watchdog-consumer.lock $ROOT_DIR/control-plane/scripts/prod_idle_watchdog_handoff_consumer_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-idle-watchdog-consumer.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog handoff consumer ===
# === OpenClaw Agent OS Prod idle watchdog execution bridge ===
$PROD_IDLE_WATCHDOG_EXECUTION_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-idle-watchdog-execution.lock env EXECUTION_BRIDGE_MODE=activate INTERNAL_WATCHDOG_PRIMARY=false TARGET_CRON_NAME=Autopilot\\ sequential\\ delivery\\ cycle $ROOT_DIR/control-plane/scripts/prod_idle_watchdog_execution_bridge_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-idle-watchdog-execution.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog execution bridge ===
# === OpenClaw Agent OS Prod delivery ===
$PROD_DELIVERY_QUEUE_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-delivery-queue.lock $ROOT_DIR/control-plane/scripts/prod_delivery_queue_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-delivery-queue.log 2>&1
$PROD_DELIVERY_HANDOFF_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-delivery-handoff.lock $ROOT_DIR/control-plane/scripts/prod_delivery_handoff_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-delivery-handoff.log 2>&1
# === /OpenClaw Agent OS Prod delivery ===
# === OpenClaw Agent OS Prod delivery execution ===
$PROD_DELIVERY_CONSUMER_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-delivery-consumer.lock $ROOT_DIR/control-plane/scripts/prod_delivery_handoff_consumer_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-delivery-consumer.log 2>&1
$PROD_DELIVERY_EXECUTION_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-delivery-execution.lock env EXECUTION_BRIDGE_MODE=activate EXECUTION_BACKEND=agent TRIGGER_AGENT=main INTERNAL_DELIVERY_PRIMARY=false $ROOT_DIR/control-plane/scripts/prod_delivery_execution_bridge_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-delivery-execution.log 2>&1
# === /OpenClaw Agent OS Prod delivery execution ===
# === OpenClaw Agent OS Prod delivery reconcile ===
$PROD_DELIVERY_RECONCILE_SCHEDULE flock -n $OPENCLAW_HOME/runtime/agentos/prod-delivery-reconcile.lock $ROOT_DIR/control-plane/scripts/prod_delivery_reconcile_cycle.sh >> $OPENCLAW_HOME/logs/agentos-prod-delivery-reconcile.log 2>&1
# === /OpenClaw Agent OS Prod delivery reconcile ===
EOF

crontab "$tmp"
rm -f "$tmp"

echo "Installed OpenClaw cron block."
echo "Edit alert target in: $ALERTS_FILE"
echo "Test now:"
echo "  . $ALERTS_FILE && $ROOT_DIR/scripts/healthcheck_notify.sh"
