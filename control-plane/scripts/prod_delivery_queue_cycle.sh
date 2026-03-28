#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/openclaw-workspace}"
PROD_AGENTOS_DB="${PROD_AGENTOS_DB:-$PROD_OPENCLAW_HOME/runtime/agentos/prod-delivery.db}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"
BOARD_SECTIONS="${BOARD_SECTIONS:-AUTHORIZED,IN PROGRESS}"

mkdir -p "$(dirname "$PROD_AGENTOS_DB")"

echo "[prod-delivery-queue] $(date -Iseconds) start"
echo "[prod-delivery-queue] db=$PROD_AGENTOS_DB"
echo "[prod-delivery-queue] workspace=$PROD_WORKSPACE_ROOT"
echo "[prod-delivery-queue] sections=$BOARD_SECTIONS"

docker_guard_ensure "prod-delivery-queue" || true
docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-delivery-queue"

"$ROOT_DIR/control-plane/scripts/init_db.sh" --db "$PROD_AGENTOS_DB"
python3 "$ROOT_DIR/scripts/agentos.py" sync-board --db "$PROD_AGENTOS_DB" --workspace-root "$PROD_WORKSPACE_ROOT" --sections "$BOARD_SECTIONS"
python3 "$ROOT_DIR/scripts/agentos.py" supervisor-cycle --db "$PROD_AGENTOS_DB" --unsafe-mode

docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-delivery-queue"

echo "[prod-delivery-queue] $(date -Iseconds) done"
