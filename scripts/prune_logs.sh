#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-$HOME/openclaw/logs}"
COMPRESS_AFTER_DAYS="${COMPRESS_AFTER_DAYS:-2}"
DELETE_AFTER_DAYS="${DELETE_AFTER_DAYS:-30}"
MAX_INLINE_LOG_BYTES="${MAX_INLINE_LOG_BYTES:-10485760}"
KEEP_INLINE_LOG_LINES="${KEEP_INLINE_LOG_LINES:-2000}"

mkdir -p "$LOG_DIR"

# Daily OpenClaw logs are append-only; compress old files to reduce disk usage.
find "$LOG_DIR" -maxdepth 1 -type f -name "openclaw-*.log" -mtime +"$COMPRESS_AFTER_DAYS" -exec gzip -f {} \;
find "$LOG_DIR" -maxdepth 1 -type f -name "openclaw-*.log.gz" -mtime +"$DELETE_AFTER_DAYS" -delete

for log_name in healthcheck.log backup.log update.log; do
  log_path="$LOG_DIR/$log_name"
  if [ ! -f "$log_path" ]; then
    continue
  fi
  size="$(stat -c%s "$log_path")"
  if [ "$size" -le "$MAX_INLINE_LOG_BYTES" ]; then
    continue
  fi
  tmp_file="$(mktemp)"
  tail -n "$KEEP_INLINE_LOG_LINES" "$log_path" > "$tmp_file"
  mv "$tmp_file" "$log_path"
done

echo "Log pruning completed in $LOG_DIR"
