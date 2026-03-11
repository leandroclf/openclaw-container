#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_WORKSPACE_ROOT="${PROD_WORKSPACE_ROOT:-$HOME/clawd}"
PROD_AGENTOS_DB="${PROD_AGENTOS_DB:-$PROD_OPENCLAW_HOME/runtime/agentos/prod-delivery.db}"
PROD_HANDOFF_DIR="${PROD_HANDOFF_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"

mkdir -p "$(dirname "$PROD_AGENTOS_DB")" "$PROD_HANDOFF_DIR"

echo "[prod-delivery-handoff] $(date -Iseconds) start"
echo "[prod-delivery-handoff] db=$PROD_AGENTOS_DB"
echo "[prod-delivery-handoff] handoffs=$PROD_HANDOFF_DIR"

docker exec "$PROD_CONTAINER_NAME" openclaw --profile prod gateway health

python3 "$ROOT_DIR/scripts/agentos.py" export-delivery-handoff --db "$PROD_AGENTOS_DB" --workspace-root "$PROD_WORKSPACE_ROOT" --bridge-dir "$PROD_HANDOFF_DIR"

docker exec "$PROD_CONTAINER_NAME" openclaw --profile prod gateway health

echo "[prod-delivery-handoff] $(date -Iseconds) done"
