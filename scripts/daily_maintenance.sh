#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${CONTAINER:-openclaw}"
PROFILE="${PROFILE:-prod}"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
LOG_DIR="${LOG_DIR:-$OPENCLAW_HOME/logs}"
ALERT_TARGET="${ALERT_TELEGRAM_TARGET:-}"
RUN_SECRETS_AUDIT="${RUN_SECRETS_AUDIT:-1}"
RUN_PLACEHOLDER_AUDIT="${RUN_PLACEHOLDER_AUDIT:-1}"

HEALTH_RETRIES="${HEALTH_RETRIES:-6}"
HEALTH_DELAY="${HEALTH_DELAY:-5}"
AUTO_RESTART_ON_HEALTH_FAILURE="${AUTO_RESTART_ON_HEALTH_FAILURE:-1}"

TELEGRAM_CONFLICT_WINDOW_MINUTES="${TELEGRAM_CONFLICT_WINDOW_MINUTES:-15}"
TELEGRAM_CONFLICT_THRESHOLD="${TELEGRAM_CONFLICT_THRESHOLD:-4}"
DISK_THRESHOLD_PERCENT="${DISK_THRESHOLD_PERCENT:-90}"

log() {
  echo "[$(date -Is)] $*"
}

"$ROOT_DIR/scripts/sync_runtime_config.sh" >/dev/null

send_alert() {
  local message="$1"
  if [ -z "$ALERT_TARGET" ]; then
    return 0
  fi
  docker exec "$CONTAINER" openclaw --profile "$PROFILE" message send \
    --channel telegram --target "$ALERT_TARGET" --message "$message" >/dev/null 2>&1 || true
}

container_exists() {
  docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"
}

container_running() {
  docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"
}

ensure_container_running() {
  if ! container_exists; then
    log "ERROR: container '$CONTAINER' not found."
    send_alert "OpenClaw daily maintenance: container '$CONTAINER' not found on $(hostname)."
    exit 1
  fi

  if ! container_running; then
    log "Container '$CONTAINER' is stopped; starting."
    docker start "$CONTAINER" >/dev/null
    sleep 10
  fi
}

run_health() {
  CHECK_CHANNEL_PROBE=1 "$ROOT_DIR/scripts/healthcheck.sh" "$HEALTH_RETRIES" "$HEALTH_DELAY"
}

validate_config_runtime() {
  local out
  if ! out="$(docker exec "$CONTAINER" openclaw --profile "$PROFILE" config validate --json 2>/dev/null)"; then
    log "ERROR: config validate command failed."
    send_alert "OpenClaw daily maintenance: config validate failed on $(hostname)."
    return 1
  fi

  if ! echo "$out" | grep -q '"valid":true'; then
    log "ERROR: runtime config is invalid."
    send_alert "OpenClaw daily maintenance: runtime config INVALID on $(hostname)."
    return 1
  fi

  log "Config validate passed."
  return 0
}

verify_health_with_recovery() {
  if run_health; then
    log "Health check passed."
    return 0
  fi

  log "ERROR: health check failed."
  if [ "$AUTO_RESTART_ON_HEALTH_FAILURE" != "1" ]; then
    send_alert "OpenClaw daily maintenance: healthcheck failed on $(hostname) and auto-restart is disabled."
    exit 1
  fi

  log "Attempting one safe restart for '$CONTAINER'."
  docker restart "$CONTAINER" >/dev/null
  sleep 10

  if run_health; then
    log "Health recovered after restart."
    send_alert "OpenClaw daily maintenance: health recovered after restart on $(hostname)."
    return 0
  fi

  log "ERROR: health still failing after restart."
  send_alert "OpenClaw daily maintenance: health still failing after restart on $(hostname)."
  exit 1
}

check_disk_usage() {
  mkdir -p "$LOG_DIR"
  local used
  used="$(df -P "$OPENCLAW_HOME" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
  log "Disk usage at $OPENCLAW_HOME: ${used}%"
  if [ "${used:-0}" -ge "$DISK_THRESHOLD_PERCENT" ]; then
    log "Disk usage is high; running prune_logs.sh."
    "$ROOT_DIR/scripts/prune_logs.sh" || true
    send_alert "OpenClaw daily maintenance: disk usage at ${used}% on $(hostname); log pruning executed."
  fi
}

check_telegram_conflicts() {
  local conflicts
  conflicts="$(docker logs --since "${TELEGRAM_CONFLICT_WINDOW_MINUTES}m" "$CONTAINER" 2>&1 | grep -c 'getUpdates conflict' || true)"
  log "Telegram getUpdates conflicts (last ${TELEGRAM_CONFLICT_WINDOW_MINUTES}m): $conflicts"
  if [ "${conflicts:-0}" -ge "$TELEGRAM_CONFLICT_THRESHOLD" ]; then
    log "WARN: recurring Telegram getUpdates conflicts detected."
    send_alert "OpenClaw daily maintenance: detected ${conflicts} Telegram getUpdates conflicts in ${TELEGRAM_CONFLICT_WINDOW_MINUTES}m. Check for another bot instance using the same token."
  fi
}

check_duplicate_openclaw_instances() {
  local count
  count="$(docker ps --format '{{.Names}}' | grep -Ec '^openclaw($|-)' || true)"
  log "Running OpenClaw containers: $count"
  if [ "${count:-0}" -gt 1 ]; then
    log "WARN: multiple OpenClaw containers are running."
    send_alert "OpenClaw daily maintenance: ${count} OpenClaw containers are running. This can cause Telegram getUpdates conflicts."
  fi
}

run_secrets_audit() {
  local audit_json
  local audit_file
  local counts
  local plaintext unresolved shadowed

  if [ "$RUN_SECRETS_AUDIT" != "1" ]; then
    log "Secrets audit disabled (RUN_SECRETS_AUDIT=0)."
    return 0
  fi

  if ! audit_json="$(docker exec "$CONTAINER" openclaw --profile "$PROFILE" secrets audit --json 2>/dev/null)"; then
    log "WARN: secrets audit command failed."
    send_alert "OpenClaw daily maintenance: secrets audit command failed on $(hostname)."
    return 0
  fi

  audit_file="$(mktemp)"
  printf '%s' "$audit_json" > "$audit_file"
  if ! counts="$(python3 - "$audit_file" <<'PY' 2>/dev/null
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
d = json.loads(path.read_text(encoding="utf-8"))
s = d.get("summary", {})
print(s.get("plaintextCount", 0), s.get("unresolvedRefCount", 0), s.get("shadowedRefCount", 0))
PY
)"; then
    rm -f "$audit_file"
    log "WARN: unable to parse secrets audit output."
    return 0
  fi
  rm -f "$audit_file"

  plaintext="$(echo "$counts" | awk '{print $1}')"
  unresolved="$(echo "$counts" | awk '{print $2}')"
  shadowed="$(echo "$counts" | awk '{print $3}')"
  log "Secrets audit summary: plaintext=${plaintext} unresolved=${unresolved} shadowed=${shadowed}"

  # openclaw secrets audit can classify ${VAR} placeholders as plaintext on some versions.
  # We alert only for unresolved/shadowed refs; placeholder policy is enforced separately.
  if [ "${unresolved:-0}" -gt 0 ] || [ "${shadowed:-0}" -gt 0 ]; then
    send_alert "OpenClaw daily maintenance: secrets audit findings on $(hostname) (unresolved=${unresolved}, shadowed=${shadowed})."
  elif [ "${plaintext:-0}" -gt 0 ]; then
    log "INFO: plaintext findings present; relying on placeholder audit for policy enforcement."
  fi
}

run_placeholder_audit() {
  local audit_out

  if [ "$RUN_PLACEHOLDER_AUDIT" != "1" ]; then
    log "Placeholder audit disabled (RUN_PLACEHOLDER_AUDIT=0)."
    return 0
  fi

  if ! audit_out="$(python3 "$ROOT_DIR/scripts/check_secret_placeholders.py" 2>&1)"; then
    log "WARN: placeholder audit failed."
    log "$audit_out"
    send_alert "OpenClaw daily maintenance: placeholder audit failed on $(hostname). Review secrets placeholders in openclaw.json."
    return 0
  fi

  log "Placeholder audit passed."
}

print_runtime_summary() {
  log "Runtime summary:"
  docker ps --filter "name=^/${CONTAINER}$" --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
  docker exec "$CONTAINER" openclaw --profile "$PROFILE" config get agents.defaults.model
}

log "Daily maintenance started."
docker context ls
docker context show
ensure_container_running
verify_health_with_recovery
validate_config_runtime
run_secrets_audit
run_placeholder_audit
check_disk_usage
check_duplicate_openclaw_instances
check_telegram_conflicts
print_runtime_summary
log "Daily maintenance finished."
