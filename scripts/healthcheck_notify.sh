#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${ALERT_TELEGRAM_TARGET:-}"
CONTAINER="${CONTAINER:-openclaw}"
PROFILE="${PROFILE:-prod}"

format_reply() {
  local channel="$1"
  local artifact_ref="${2:-}"
  if [ -n "$artifact_ref" ]; then
    python3 "$ROOT_DIR/scripts/before_agent_reply.py" --channel "$channel" --artifact-ref "$artifact_ref"
  else
    python3 "$ROOT_DIR/scripts/before_agent_reply.py" --channel "$channel"
  fi
}

if output=$("$ROOT_DIR/scripts/healthcheck.sh" 2>&1); then
  echo "$output"
  exit 0
fi

echo "$output" >&2

if [ -n "$TARGET" ]; then
  msg="OpenClaw healthcheck failed on $(hostname) at $(date -Is)."
  formatted="$(
    printf '%s' "$msg" | format_reply telegram "artifact://healthcheck" 2>/dev/null \
      || printf '%s' "$msg"
  )"
  docker exec "$CONTAINER" openclaw --profile "$PROFILE" message send \
    --channel telegram --target "$TARGET" --message "$formatted" || true
fi

exit 1
