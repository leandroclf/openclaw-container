# OpenClaw Ops Checklist

## Daily
- Health: `./scripts/healthcheck.sh`
- Logs: `./scripts/logs.sh`
- Cron process: `service cron status`

## Weekly
- Update image + restart: `./scripts/update.sh`
- Backup state: `./scripts/backup.sh`

## After changes
- `docker exec openclaw openclaw --profile prod status`
- If Telegram issues: check pairing + allowlist.

## When OAuth expires
- Re-run: `docker exec -it openclaw openclaw --profile prod onboard --auth-choice openai-codex`

## Alerts (optional)
- Use `scripts/healthcheck_notify.sh` with `ALERT_TELEGRAM_TARGET`.
- Install cron block via `scripts/install_cron.sh`.
- Example crontab in `cron/cron.example`.

## Replication
- Use `RUNBOOK.md` for full step-by-step setup on a new host.
