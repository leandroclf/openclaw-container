# OpenClaw (WSL + Docker)

This repository contains the Docker image setup and operational guide for
running OpenClaw 24/7 inside WSL (Ubuntu-24.04).

## Quick start

### 1) Build the image (legacy builder only)
```bash
DOCKER_BUILDKIT=0 docker build --build-arg OPENCLAW_VERSION=latest -t openclaw-secure:latest .
```

### 2) Prepare folders
```bash
mkdir -p ~/openclaw/{data,logs,config,runtime}
mkdir -p ~/openclaw/runtime/{gemini,config,cache,pki}
mkdir -p ~/clawd
chmod 700 ~/openclaw ~/openclaw/data ~/openclaw/runtime
chmod 600 ~/openclaw/.env
```

### 3) Run (hardened)
```bash
docker rm -f openclaw 2>/dev/null || true
docker run -d --name openclaw --restart unless-stopped \
  --env-file ~/openclaw/.env \
  -e XDG_CONFIG_HOME=/home/node/.openclaw/config \
  -e XDG_CACHE_HOME=/home/node/.openclaw/cache \
  -e XDG_RUNTIME_DIR=/tmp \
  --read-only --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v ~/openclaw/data:/home/node/.openclaw-prod \
  -v ~/openclaw/runtime:/home/node/.openclaw \
  -v ~/openclaw/runtime/gemini:/home/node/.gemini \
  -v ~/openclaw/runtime/pki:/home/node/.pki \
  -v ~/openclaw/logs:/tmp/openclaw \
  -v ~/clawd:/home/node/clawd \
  openclaw-secure --profile prod gateway run --bind loopback --port 18789
```

### 4) Health check
```bash
docker exec openclaw openclaw --profile prod gateway health
```
If you see a 1006 error immediately after restart, wait 5-10 seconds and retry.

### 5) Browser automation (no human action)
```bash
docker exec openclaw openclaw --profile prod browser create-profile --name openclaw-auto --driver openclaw
docker exec openclaw openclaw --profile prod config set browser.defaultProfile openclaw-auto
docker exec openclaw openclaw --profile prod browser --browser-profile openclaw-auto start --json
docker exec openclaw openclaw --profile prod browser --browser-profile openclaw-auto stop --json
```
If `create-profile` returns "already exists", continue with the next command.
Keep profile `chrome` only for optional manual extension takeover.

## Secrets
- Use `~/openclaw/.env` for all secrets.
- See `.env.example` for required keys.
- Optional keys for advanced features: `OPENAI_API_KEY`, `GH_TOKEN`, `GITHUB_TOKEN`.
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
For phased architecture evolution (no-downtime rollout), see
`docs/architecture/README.md`.
For strict production change guardrails and parallel deployment, see:
- `docs/operations/PRODUCTION_CHANGE_POLICY.md`
- `docs/operations/BLUE_GREEN_WSL_DOCKER_DESKTOP.md`
- `docs/operations/TEST_STRATEGY.md`
- `docs/operations/PROMOTION_ROLLBACK_CHECKLIST.md`
- `docs/operations/COMPOSE_BLUE_GREEN_USAGE.md`
- `docs/operations/AGENTOS_GREEN_ROLLOUT_PLAN.md`
- `docs/operations/VALIDATION_EVIDENCE_2026-02-28.md`
- `docs/operations/TOKEN_COST_REDUCTION_STRATEGY.md`
- `docs/architecture/OpenClaw_AgentOS_Migration.md`
- `control-plane/README.md`

## Scripts
- `./scripts/update.sh` build (latest stable) + restart + health
- `./scripts/restart.sh` restart + health
- `./scripts/sync_runtime_config.sh` copy `~/openclaw/data/openclaw.json` into
  the runtime state paths expected by current OpenClaw releases
- Canonical runtime config lives in `~/openclaw/data/openclaw.json`; treat
  `~/openclaw/config/config.yaml` as a legacy host-side surface unless you
  explicitly synchronize it before a rollout.
- `./scripts/healthcheck.sh` gateway health + channel probe with retries
- `./scripts/daily_maintenance.sh` daily safe maintenance with auto-recovery checks + secrets placeholder policy audit
- `./scripts/check_secret_placeholders.py` validate that sensitive config paths use `${VAR}` placeholders (no literal secrets/SecretRef objects)
- `./scripts/logs.sh` tail latest log (add `--follow`)
- `./scripts/backup.sh` create a verified OpenClaw backup archive using the
  native backup CLI
- `./scripts/install_cron.sh` install/update the full production cron layout
  (container ops + active Agent OS host-side lanes)
- `./scripts/prune_logs.sh` compress/prune old logs
- `./scripts/model_router.py` objective-based model routing (dry-run or apply)
- `./scripts/model_route_apply.sh <objective>` apply routing + callbacks
- `./scripts/agentos.py` Agent OS control-plane primitives (queue, events, preflight, scheduler, Telegram envelope)
- `control-plane/scripts/*.sh` thin wrappers for Agent OS DB init, schema validation, preflight, and supervisor cycle
- `control-plane/config/workflow_registry.json` low-risk workflow registry for Green rollout
- `control-plane/scripts/run_workflow.sh` execute one registered low-risk workflow via Agent OS
- `./scripts/test_gate.sh` run unit/regression tests (add
  `--with-integration` for container guardrail checks)

## Compose templates (blue/green)
- Compose file: `compose/docker-compose.blue-green.yml`
- Env templates:
  - `compose/blue.env.example`
  - `compose/green.env.example`
- Safe usage guide: `docs/operations/COMPOSE_BLUE_GREEN_USAGE.md`

## Model routing (quality + cost strategy)
Policy files live in `ops/model-routing/`.

Quick examples:
```bash
./scripts/model_router.py --list-objectives
./scripts/model_router.py --objective balanced_default
./scripts/model_router.py --objective coding_quality --apply --run-callbacks
```

`./scripts/install_cron.sh` applies three automatic routing windows:
- baseline after daily update (`cost_optimized`)
- business hours (`balanced_default`)
- off-hours (`cost_optimized`)

## Ops checklist
See `CHECKLIST.md`.

## Optional alerts
- `./scripts/healthcheck_notify.sh` will send a Telegram alert if
  `ALERT_TELEGRAM_TARGET` is set.
- See `cron/cron.example` for sample scheduling.
