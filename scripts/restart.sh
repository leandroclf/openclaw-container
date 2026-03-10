#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-openclaw}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${PROFILE:-prod}"

"$ROOT_DIR/scripts/sync_runtime_config.sh" >/dev/null

validate_json="$(docker exec "$CONTAINER" openclaw --profile "$PROFILE" config validate --json 2>/dev/null || true)"
if ! echo "$validate_json" | grep -q '"valid":true'; then
  echo "ERROR: runtime config is invalid; refusing restart." >&2
  exit 1
fi

docker restart "$CONTAINER"
"$ROOT_DIR/scripts/healthcheck.sh"
