#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
BACKUP_DIR="${BACKUP_DIR:-$OPENCLAW_HOME/backups}"
INCLUDE_CREDENTIALS="${INCLUDE_CREDENTIALS:-0}"

mkdir -p "$BACKUP_DIR"

stamp=$(date +%Y%m%d-%H%M%S)
backup_file="$BACKUP_DIR/openclaw-backup-$stamp.tar.gz"

excludes=()
if [ "$INCLUDE_CREDENTIALS" -ne 1 ]; then
  excludes+=(--exclude "$OPENCLAW_HOME/data/credentials")
fi

# Backup core state; logs are omitted by default
if tar -czf "$backup_file" "${excludes[@]}" \
  "$OPENCLAW_HOME/data" \
  "$OPENCLAW_HOME/runtime" \
  "$OPENCLAW_HOME/config"; then
  echo "Backup created: $backup_file"
else
  echo "Backup failed: $backup_file" >&2
  exit 1
fi
