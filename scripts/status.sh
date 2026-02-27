#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-openclaw}"
PROFILE="${PROFILE:-prod}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== docker ps =="
docker ps

echo "== gateway health =="
"$ROOT_DIR/scripts/healthcheck.sh"

echo "== openclaw status =="
docker exec "$CONTAINER" openclaw --profile "$PROFILE" status --deep

echo "== channel probes =="
docker exec "$CONTAINER" openclaw --profile "$PROFILE" channels status --probe
