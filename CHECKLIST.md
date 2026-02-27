# OpenClaw Ops Checklist

## Daily
- Health + channel probe: `./scripts/healthcheck.sh`
- Logs: `./scripts/logs.sh`
- Cron process: `service cron status`

## Weekly
- Update image + restart: `./scripts/update.sh`
- Backup state: `./scripts/backup.sh`
- Prune/compress logs: `./scripts/prune_logs.sh`

## After changes
- `docker exec openclaw openclaw --profile prod status`
- If Telegram issues: check pairing + allowlist.

## Before any production change
- `docker context ls && docker context show`
- `docker ps --filter name=openclaw`
- `docker exec openclaw openclaw --profile prod gateway health`
- Never stop/remove `openclaw` before candidate (`openclaw-next`) passes tests.

## Parallel validation (mandatory)
- Run candidate in parallel: `openclaw-next` on port `28789` with isolated
  volumes under `~/openclaw-next` and isolated workspace `~/clawd-next`.
- Use non-production Telegram token for candidate (or disable Telegram).
- Validate health/status/logs on candidate before any cutover decision.
- Run test gates: `./scripts/test_gate.sh --with-integration`.
- Follow `docs/operations/BLUE_GREEN_WSL_DOCKER_DESKTOP.md` step by step.
- For cutover, follow `docs/operations/PROMOTION_ROLLBACK_CHECKLIST.md`.
- If using compose templates, follow `docs/operations/COMPOSE_BLUE_GREEN_USAGE.md`.

## When OAuth expires
- Re-run: `docker exec -it openclaw openclaw --profile prod onboard --auth-choice openai-codex`

## Alerts (optional)
- Use `scripts/healthcheck_notify.sh` with `ALERT_TELEGRAM_TARGET`.
- Install cron block via `scripts/install_cron.sh`.
- Example crontab in `cron/cron.example`.

## Replication
- Use `RUNBOOK.md` for full step-by-step setup on a new host.
