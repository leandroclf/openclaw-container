#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROFILE="${PROFILE:-prod}"
CRON_ID="${CRON_ID:-e6d5079d-3eaa-46fa-ac4a-4f77add89b18}"
MESSAGE_FILE="${MESSAGE_FILE:-$ROOT_DIR/control-plane/config/delivery_executor_message.txt}"

message="$(cat "$MESSAGE_FILE")"
docker exec openclaw openclaw --profile "$PROFILE" cron edit "$CRON_ID" --message "$message"
echo "[patch-internal-delivery-executor] updated"
