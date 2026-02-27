#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-openclaw}"
PROFILE="${PROFILE:-prod}"
RETRIES="${1:-6}"
DELAY="${2:-5}"
CHECK_CHANNEL_PROBE="${CHECK_CHANNEL_PROBE:-1}"

for i in $(seq 1 "$RETRIES"); do
  if output=$(docker exec "$CONTAINER" openclaw --profile "$PROFILE" gateway health 2>&1); then
    echo "$output"
    if [ "$CHECK_CHANNEL_PROBE" = "1" ]; then
      if ! probe=$(docker exec "$CONTAINER" openclaw --profile "$PROFILE" channels status --probe --json 2>&1); then
        echo "$probe" >&2
        exit 1
      fi
    fi
    exit 0
  fi
  echo "health attempt $i failed; retrying in ${DELAY}s" >&2
  sleep "$DELAY"
done

echo "healthcheck failed after ${RETRIES} attempts" >&2
exit 1
