#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/openclaw-workspace}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"

mkdir -p "$PROD_OPENCLAW_HOME/runtime/agentos" "$PROD_OPENCLAW_HOME/logs"

echo "[prod-idle-watchdog-policy] $(date -Iseconds) start"
echo "[prod-idle-watchdog-policy] workspace=$PROD_WORKSPACE_ROOT"

docker_guard_ensure "prod-idle-watchdog-policy" || true
docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-idle-watchdog-policy"

python3 "$ROOT_DIR/scripts/idle_watchdog_policy_wrapper.py" --workspace-root "$PROD_WORKSPACE_ROOT"

docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-idle-watchdog-policy"

echo "[prod-idle-watchdog-policy] $(date -Iseconds) done"
