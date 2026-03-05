#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-openclaw-secure:latest}"
CONTAINER="${CONTAINER:-openclaw}"
PROFILE="${PROFILE:-prod}"
PORT="${PORT:-18789}"
BIND="${BIND:-loopback}"
OPENCLAW_VERSION="${OPENCLAW_VERSION:-}"
GEMINI_CLI_VERSION="${GEMINI_CLI_VERSION:-}"
PIDS_LIMIT="${PIDS_LIMIT:-512}"

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
ENV_FILE="${ENV_FILE:-$OPENCLAW_HOME/.env}"
WORKSPACE="${WORKSPACE:-$HOME/clawd}"
GEMINI_HOME_DIR="${GEMINI_HOME_DIR:-$OPENCLAW_HOME/runtime/gemini}"
XDG_CONFIG_DIR="${XDG_CONFIG_DIR:-$OPENCLAW_HOME/runtime/config}"
XDG_CACHE_DIR="${XDG_CACHE_DIR:-$OPENCLAW_HOME/runtime/cache}"
PKI_DIR="${PKI_DIR:-$OPENCLAW_HOME/runtime/pki}"
NPM_CACHE_DIR="${NPM_CACHE_DIR:-$OPENCLAW_HOME/runtime/npm}"

mkdir -p "$OPENCLAW_HOME/data" "$OPENCLAW_HOME/logs" "$OPENCLAW_HOME/runtime" "$WORKSPACE" "$GEMINI_HOME_DIR" "$XDG_CONFIG_DIR" "$XDG_CACHE_DIR" "$PKI_DIR" "$NPM_CACHE_DIR"
chmod 700 "$OPENCLAW_HOME" "$OPENCLAW_HOME/data" "$OPENCLAW_HOME/runtime"
if [ -f "$ENV_FILE" ]; then
  chmod 600 "$ENV_FILE"
fi

if [ -z "$OPENCLAW_VERSION" ]; then
  OPENCLAW_VERSION="$(npm view openclaw version 2>/dev/null || true)"
fi
if [ -z "$OPENCLAW_VERSION" ]; then
  OPENCLAW_VERSION="latest"
fi
if [ -z "$GEMINI_CLI_VERSION" ]; then
  GEMINI_CLI_VERSION="$(npm view @google/gemini-cli version 2>/dev/null || true)"
fi
if [ -z "$GEMINI_CLI_VERSION" ]; then
  GEMINI_CLI_VERSION="latest"
fi

DOCKER_BUILDKIT=0 docker build --pull \
  --build-arg OPENCLAW_VERSION="$OPENCLAW_VERSION" \
  --build-arg GEMINI_CLI_VERSION="$GEMINI_CLI_VERSION" \
  -t "$IMAGE" "$ROOT_DIR"

docker rm -f "$CONTAINER" 2>/dev/null || true

docker run -d --name "$CONTAINER" --restart unless-stopped \
  --env-file "$ENV_FILE" \
  -e XDG_CONFIG_HOME=/home/node/.openclaw/config \
  -e XDG_CACHE_HOME=/home/node/.openclaw/cache \
  -e XDG_RUNTIME_DIR=/tmp \
  -e NPM_CONFIG_CACHE=/home/node/.npm \
  --read-only --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit "$PIDS_LIMIT" \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v "$OPENCLAW_HOME/data":/home/node/.openclaw-prod \
  -v "$OPENCLAW_HOME/runtime":/home/node/.openclaw \
  -v "$GEMINI_HOME_DIR":/home/node/.gemini \
  -v "$PKI_DIR":/home/node/.pki \
  -v "$NPM_CACHE_DIR":/home/node/.npm \
  -v "$OPENCLAW_HOME/logs":/tmp/openclaw \
  -v "$WORKSPACE":/home/node/clawd \
  "$IMAGE" --profile "$PROFILE" gateway run --bind "$BIND" --port "$PORT"

validate_json="$(docker exec "$CONTAINER" openclaw --profile "$PROFILE" config validate --json 2>/dev/null || true)"
if ! echo "$validate_json" | grep -q '"valid":true'; then
  echo "ERROR: runtime config validation failed after update." >&2
  exit 1
fi

"$ROOT_DIR/scripts/healthcheck.sh"

# Keep browser automation in managed OpenClaw mode (no extension dependency).
docker exec "$CONTAINER" openclaw --profile "$PROFILE" browser create-profile --name openclaw-auto --driver openclaw >/dev/null 2>&1 || true
docker exec "$CONTAINER" openclaw --profile "$PROFILE" config set browser.defaultProfile openclaw-auto >/dev/null
