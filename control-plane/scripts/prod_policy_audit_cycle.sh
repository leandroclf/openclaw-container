#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/openclaw-workspace}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"

mkdir -p "$PROD_OPENCLAW_HOME/runtime/agentos" "$PROD_OPENCLAW_HOME/logs"

echo "[prod-policy-audit] $(date -Iseconds) start"
echo "[prod-policy-audit] workspace=$PROD_WORKSPACE_ROOT"

docker_guard_ensure "prod-policy-audit" || true
docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-policy-audit"

(
  cd "$PROD_WORKSPACE_ROOT"
  python3 ops/multiagent/delivery/scripts/deploy_audit_policy_wrapper.py
)

docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-policy-audit"

echo "[prod-policy-audit] $(date -Iseconds) done"
