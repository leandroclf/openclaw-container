#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-openclaw}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker restart "$CONTAINER"
"$ROOT_DIR/scripts/healthcheck.sh"
