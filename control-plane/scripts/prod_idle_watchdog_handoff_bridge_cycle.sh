#!/usr/bin/env bash
set -euo pipefail

PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$HOME/clawd}"
BRIDGE_DIR="${BRIDGE_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"

docker exec openclaw openclaw --profile prod gateway health >/dev/null

python3 /home/leandro/openclaw-container/scripts/idle_watchdog_handoff_bridge.py \
  --workspace-root "$WORKSPACE_ROOT" \
  --bridge-dir "$BRIDGE_DIR"

docker exec openclaw openclaw --profile prod gateway health >/dev/null
