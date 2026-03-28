#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
GREEN_OPENCLAW_HOME="${GREEN_OPENCLAW_HOME:-$HOME/openclaw-next}"
GREEN_WORKSPACE_ROOT="${GREEN_WORKSPACE_ROOT:-$HOME/clawd-next}"
GREEN_AGENTOS_DB="${GREEN_AGENTOS_DB:-$GREEN_OPENCLAW_HOME/runtime/agentos/green-observe.db}"
GREEN_LOG_DIR="${GREEN_LOG_DIR:-$GREEN_OPENCLAW_HOME/logs}"
GREEN_CONTAINER_NAME="${GREEN_CONTAINER_NAME:-openclaw-next}"

mkdir -p "$(dirname "$GREEN_AGENTOS_DB")" "$GREEN_LOG_DIR"

echo "[green-observe] $(date -Iseconds) start"
echo "[green-observe] db=$GREEN_AGENTOS_DB"
echo "[green-observe] workspace=$GREEN_WORKSPACE_ROOT"

docker_guard_ensure "green-observe" || true
docker_guard_health_or_skip "$GREEN_CONTAINER_NAME" prod "green-observe"

"$ROOT_DIR/control-plane/scripts/init_db.sh" --db "$GREEN_AGENTOS_DB"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$GREEN_AGENTOS_DB" --name daily_ops_state_lint --workspace-root "$GREEN_WORKSPACE_ROOT"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$GREEN_AGENTOS_DB" --name daily_summary_rotation --workspace-root "$GREEN_WORKSPACE_ROOT"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$GREEN_AGENTOS_DB" --name product_progress_snapshot --workspace-root "$GREEN_WORKSPACE_ROOT"
"$ROOT_DIR/control-plane/scripts/run_workflow.sh" --db "$GREEN_AGENTOS_DB" --name autonomy_supervisor --workspace-root "$GREEN_WORKSPACE_ROOT"

docker_guard_health_or_skip "$GREEN_CONTAINER_NAME" prod "green-observe"

echo "[green-observe] $(date -Iseconds) done"
