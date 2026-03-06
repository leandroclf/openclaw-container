#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/clawd}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"

mkdir -p "$PROD_OPENCLAW_HOME/runtime/agentos" "$PROD_OPENCLAW_HOME/logs"

echo "[prod-policy-audit] $(date -Iseconds) start"
echo "[prod-policy-audit] workspace=$PROD_WORKSPACE_ROOT"

docker exec "$PROD_CONTAINER_NAME" openclaw --profile prod gateway health

(
  cd "$PROD_WORKSPACE_ROOT"
  python3 ops/multiagent/delivery/scripts/deploy_audit_policy_wrapper.py
)

docker exec "$PROD_CONTAINER_NAME" openclaw --profile prod gateway health

echo "[prod-policy-audit] $(date -Iseconds) done"
