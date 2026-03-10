#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
BACKUP_DIR="${BACKUP_DIR:-$OPENCLAW_HOME/backups}"
PROFILE="${PROFILE:-prod}"
ONLY_CONFIG="${ONLY_CONFIG:-0}"
INCLUDE_WORKSPACE="${INCLUDE_WORKSPACE:-0}"
VERIFY_BACKUP="${VERIFY_BACKUP:-1}"
RUNTIME_BACKUP_DIR="${RUNTIME_BACKUP_DIR:-$OPENCLAW_HOME/runtime/backups}"

mkdir -p "$BACKUP_DIR"
if [ -e "$RUNTIME_BACKUP_DIR" ] && [ ! -d "$RUNTIME_BACKUP_DIR" ]; then
  mv "$RUNTIME_BACKUP_DIR" "${RUNTIME_BACKUP_DIR}.legacy-file-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$RUNTIME_BACKUP_DIR"

stamp="$(date +%Y%m%d-%H%M%S)"
archive_name="openclaw-backup-$stamp.tar.gz"
container_output="/home/node/.openclaw/backups/$archive_name"
staged_output="$RUNTIME_BACKUP_DIR/$archive_name"
final_output="$BACKUP_DIR/$archive_name"

cmd=(docker exec openclaw openclaw --profile "$PROFILE" backup create --output "$container_output")

if [ "$ONLY_CONFIG" -eq 1 ]; then
  cmd+=(--only-config)
fi
if [ "$INCLUDE_WORKSPACE" -ne 1 ]; then
  cmd+=(--no-include-workspace)
fi
if [ "$VERIFY_BACKUP" -eq 1 ]; then
  cmd+=(--verify)
fi

"${cmd[@]}"

if [ ! -f "$staged_output" ]; then
  echo "ERROR: staged backup not found at $staged_output" >&2
  exit 1
fi

mv "$staged_output" "$final_output"
echo "Backup created: $final_output"
