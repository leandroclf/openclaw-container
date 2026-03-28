#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/control-plane/scripts/docker_guard.sh"
PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$HOME/openclaw-workspace}"
BRIDGE_DIR="${BRIDGE_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"

docker_guard_ensure "prod-idle-watchdog-handoff-bridge" || true
docker_guard_health_or_skip openclaw prod "prod-idle-watchdog-handoff-bridge"

python3 /home/leandro/openclaw-container/scripts/idle_watchdog_handoff_bridge.py \
  --workspace-root "$WORKSPACE_ROOT" \
  --bridge-dir "$BRIDGE_DIR"

docker_guard_health_or_skip openclaw prod "prod-idle-watchdog-handoff-bridge"
