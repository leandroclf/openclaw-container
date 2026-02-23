#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${ALERT_TELEGRAM_TARGET:-}"
CONTAINER="${CONTAINER:-openclaw}"
PROFILE="${PROFILE:-prod}"

if output=$("$ROOT_DIR/scripts/healthcheck.sh" 2>&1); then
  echo "$output"
  exit 0
fi

echo "$output" >&2

if [ -n "$TARGET" ]; then
  msg="OpenClaw healthcheck failed on $(hostname) at $(date -Is)."
  docker exec "$CONTAINER" openclaw --profile "$PROFILE" message send \
    --channel telegram --target "$TARGET" --message "$msg" || true
fi

exit 1
