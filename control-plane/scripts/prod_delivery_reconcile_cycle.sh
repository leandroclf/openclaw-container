#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_AGENTOS_DB="${PROD_AGENTOS_DB:-$PROD_OPENCLAW_HOME/runtime/agentos/prod-delivery.db}"
PROD_HANDOFF_DIR="${PROD_HANDOFF_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"

mkdir -p "$(dirname "$PROD_AGENTOS_DB")" "$PROD_HANDOFF_DIR"

echo "[prod-delivery-reconcile] $(date -Iseconds) start"
echo "[prod-delivery-reconcile] db=$PROD_AGENTOS_DB"
echo "[prod-delivery-reconcile] handoffs=$PROD_HANDOFF_DIR"

docker_guard_ensure "prod-delivery-reconcile" || true
docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-delivery-reconcile"

python3 "$ROOT_DIR/scripts/delivery_result_reconcile.py" --db "$PROD_AGENTOS_DB" --bridge-dir "$PROD_HANDOFF_DIR"

docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-delivery-reconcile"

echo "[prod-delivery-reconcile] $(date -Iseconds) done"
