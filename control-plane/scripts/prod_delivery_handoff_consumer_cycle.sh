#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
PROD_HANDOFF_DIR="${PROD_HANDOFF_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"
PROD_CONTAINER_NAME="${PROD_CONTAINER_NAME:-openclaw}"

mkdir -p "$PROD_HANDOFF_DIR"

echo "[prod-delivery-consumer] $(date -Iseconds) start"
echo "[prod-delivery-consumer] handoffs=$PROD_HANDOFF_DIR"

docker_guard_ensure "prod-delivery-consumer" || true
docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-delivery-consumer"

python3 "$ROOT_DIR/scripts/delivery_handoff_consumer.py" --bridge-dir "$PROD_HANDOFF_DIR"

docker_guard_health_or_skip "$PROD_CONTAINER_NAME" prod "prod-delivery-consumer"

echo "[prod-delivery-consumer] $(date -Iseconds) done"
