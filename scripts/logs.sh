#!/usr/bin/env bash
set -euo pipefail

FOLLOW="${1:-}"
LOG_DIR="${LOG_DIR:-$HOME/openclaw/logs}"

latest_log=""
if [ -d "$LOG_DIR" ]; then
  latest_log=$(ls -t "$LOG_DIR"/openclaw-*.log 2>/dev/null | head -n 1 || true)
fi

if [ -n "$latest_log" ]; then
  if [ "$FOLLOW" = "--follow" ] || [ "$FOLLOW" = "-f" ]; then
    tail -f "$latest_log"
  else
    tail -n 200 "$latest_log"
  fi
else
  if [ "$FOLLOW" = "--follow" ] || [ "$FOLLOW" = "-f" ]; then
    docker logs -f openclaw
  else
    docker logs --tail 200 openclaw
  fi
fi
