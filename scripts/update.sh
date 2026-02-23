#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-openclaw-secure:latest}"
CONTAINER="${CONTAINER:-openclaw}"
PROFILE="${PROFILE:-prod}"
PORT="${PORT:-18789}"
BIND="${BIND:-loopback}"

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
ENV_FILE="${ENV_FILE:-$OPENCLAW_HOME/.env}"
WORKSPACE="${WORKSPACE:-$HOME/clawd}"

mkdir -p "$OPENCLAW_HOME/data" "$OPENCLAW_HOME/logs" "$OPENCLAW_HOME/runtime" "$WORKSPACE"
chmod 700 "$OPENCLAW_HOME" "$OPENCLAW_HOME/data" "$OPENCLAW_HOME/runtime"
if [ -f "$ENV_FILE" ]; then
  chmod 600 "$ENV_FILE"
fi

DOCKER_BUILDKIT=0 docker build -t "$IMAGE" "$ROOT_DIR"

docker rm -f "$CONTAINER" 2>/dev/null || true

docker run -d --name "$CONTAINER" --restart unless-stopped \
  --env-file "$ENV_FILE" \
  --read-only --cap-drop ALL \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v "$OPENCLAW_HOME/data":/home/node/.openclaw-prod \
  -v "$OPENCLAW_HOME/runtime":/home/node/.openclaw \
  -v "$OPENCLAW_HOME/logs":/tmp/openclaw \
  -v "$WORKSPACE":/home/node/clawd \
  openclaw-secure --profile "$PROFILE" gateway run --bind "$BIND" --port "$PORT"

"$ROOT_DIR/scripts/healthcheck.sh"
