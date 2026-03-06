#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/clawd}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"

mkdir -p "$PROD_OPENCLAW_HOME/runtime/agentos" "$PROD_OPENCLAW_HOME/logs"

echo "[prod-autopilot-sla] $(date -Iseconds) start"
echo "[prod-autopilot-sla] workspace=$PROD_WORKSPACE_ROOT"

docker exec "$PROD_CONTAINER_NAME" openclaw --profile prod gateway health

python3 "$ROOT_DIR/scripts/autopilot_sla_tracker.py" --workspace-root "$PROD_WORKSPACE_ROOT" --sync-dashboard

docker exec "$PROD_CONTAINER_NAME" openclaw --profile prod gateway health

echo "[prod-autopilot-sla] $(date -Iseconds) done"
