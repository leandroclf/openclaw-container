#!/usr/bin/env bash
set -euo pipefail

PROD_OPENCLAW_HOME="${PROD_OPENCLAW_HOME:-$HOME/openclaw}"
BRIDGE_DIR="${BRIDGE_DIR:-$PROD_OPENCLAW_HOME/runtime/agentos/handoffs}"

docker exec openclaw openclaw --profile prod gateway health >/dev/null

python3 /home/leandro/openclaw-container/scripts/idle_watchdog_execution_bridge.py \
  --bridge-dir "$BRIDGE_DIR" \
  --internal-watchdog-primary true

docker exec openclaw openclaw --profile prod gateway health >/dev/null
