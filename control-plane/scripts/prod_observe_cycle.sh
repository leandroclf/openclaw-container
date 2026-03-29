#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/openclaw-workspace}"
PROD_AGENTOS_DB="${PROD_AGENTOS_DB:-$PROD_OPENCLAW_HOME/runtime/agentos/prod-observe.db}"
PROD_LOG_DIR="${PROD_LOG_DIR:-$PROD_OPENCLAW_HOME/logs}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"

mkdir -p "$(dirname "$PROD_AGENTOS_DB")" "$PROD_LOG_DIR"

echo "[prod-observe] $(date -Iseconds) start"
echo "[prod-observe] db=$PROD_AGENTOS_DB"
echo "[prod-observe] workspace=$PROD_WORKSPACE_ROOT"

docker_guard_ensure "prod-observe" || true
docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-observe"

"$ROOT_DIR/control-plane/scripts/init_db.sh" --db "$PROD_AGENTOS_DB"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$PROD_AGENTOS_DB" --name daily_ops_state_lint --workspace-root "$PROD_WORKSPACE_ROOT"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$PROD_AGENTOS_DB" --name product_progress_snapshot --workspace-root "$PROD_WORKSPACE_ROOT"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$PROD_AGENTOS_DB" --name dashboard_data_sync --workspace-root "$PROD_WORKSPACE_ROOT"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$PROD_AGENTOS_DB" --name github_ci_status_collect --workspace-root "$PROD_WORKSPACE_ROOT"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$PROD_AGENTOS_DB" --name autonomy_supervisor --workspace-root "$PROD_WORKSPACE_ROOT"

docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-observe"

echo "[prod-observe] $(date -Iseconds) done"
