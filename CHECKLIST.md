# OpenClaw Ops Checklist

## Daily
- Health: `./scripts/healthcheck.sh`
- Logs: `./scripts/logs.sh`

## Weekly
- Update image + restart: `./scripts/update.sh`
- Backup state: `./scripts/backup.sh`

## After changes
- `docker exec openclaw openclaw --profile prod status`
- If Telegram issues: check pairing + allowlist.

## When OAuth expires
- Re-run: `docker exec -it openclaw openclaw --profile prod onboard --auth-choice openai-codex`
