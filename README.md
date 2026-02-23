# OpenClaw (WSL + Docker)

This repository contains the Docker image setup and operational guide for
running OpenClaw 24/7 inside WSL (Ubuntu-24.04).

## Quick start

### 1) Build the image (legacy builder only)
```bash
DOCKER_BUILDKIT=0 docker build -t openclaw-secure:latest .
```

### 2) Prepare folders
```bash
mkdir -p ~/openclaw/{data,logs,config,runtime}
mkdir -p ~/clawd
chmod 700 ~/openclaw ~/openclaw/data ~/openclaw/runtime
chmod 600 ~/openclaw/.env
```

### 3) Run (hardened)
```bash
docker rm -f openclaw 2>/dev/null || true
docker run -d --name openclaw --restart unless-stopped \
  --env-file ~/openclaw/.env \
  --read-only --cap-drop ALL \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v ~/openclaw/data:/home/node/.openclaw-prod \
  -v ~/openclaw/runtime:/home/node/.openclaw \
  -v ~/openclaw/logs:/tmp/openclaw \
  -v ~/clawd:/home/node/clawd \
  openclaw-secure --profile prod gateway run --bind loopback --port 18789
```

### 4) Health check
```bash
docker exec openclaw openclaw --profile prod gateway health
```
If you see a 1006 error immediately after restart, wait 5-10 seconds and retry.

## Secrets
- Use `~/openclaw/.env` for all secrets.
- See `.env.example` for required keys.
- Config uses `${VAR_NAME}` placeholders (see `openclaw.json.example`).

## OAuth (OpenAI Codex)
```bash
docker exec -it openclaw openclaw --profile prod onboard --auth-choice openai-codex
```
Paste the callback URL if the CLI cannot capture it automatically in WSL.

## Logs
OpenClaw writes logs to a file (persisted on host):
```bash
tail -n 200 ~/openclaw/logs/openclaw-YYYY-MM-DD.log
```

## Operations guide
See `AGENTS.md` for the full operational checklist and rules.
For full host replication (step-by-step), see `RUNBOOK.md`.

## Scripts
- `./scripts/update.sh` build + restart + health
- `./scripts/restart.sh` restart + health
- `./scripts/healthcheck.sh` health with retries
- `./scripts/logs.sh` tail latest log (add `--follow`)
- `./scripts/backup.sh` create a tarball backup (omit credentials by default)
- `./scripts/install_cron.sh` install/update OpenClaw cron block (idempotent)

## Ops checklist
See `CHECKLIST.md`.

## Optional alerts
- `./scripts/healthcheck_notify.sh` will send a Telegram alert if
  `ALERT_TELEGRAM_TARGET` is set.
- See `cron/cron.example` for sample scheduling.
