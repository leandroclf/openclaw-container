# OpenClaw (WSL + Docker)

This repository contains the Docker image setup and operational guide for
running OpenClaw 24/7 inside WSL (Ubuntu-24.04).

## Quick start

### What the 2026.4.24 release adds for this stack
- Google Meet is now a bundled participant plugin, with personal Google auth, Chrome/Twilio realtime sessions, paired-node Chrome support, attendance/artifact exports, and recovery tooling for already-open Meet tabs.
- DeepSeek V4 Flash and V4 Pro are now in the bundled catalog, with V4 Flash as the onboarding default.
- Talk, Voice Call, and Google Meet can use realtime voice loops, which makes live sessions more interactive and better for hands-on support.
- Browser automation is more reliable: coordinate clicks, longer default action budgets, per-profile headless overrides, and steadier tab reuse/recovery are all in the release.
- Startup is lighter because model catalogs are more static, provider rows are manifest-backed, provider dependencies are lazier, and packaged installs can repair missing runtime dependencies automatically.
- The plugin SDK change that matters operationally: remove `api.registerEmbeddedExtensionFactory(...)` from bundled plugin logic and use `api.registerAgentToolResultMiddleware(...)` instead.
- In this host, keep `openclaw doctor --fix` in the update path and let it migrate legacy layout drift. The current Telegram config should use `channels.telegram.streaming.mode` instead of the old scalar `streaming` value, and the bundled `acpx` plugin config now accepts only the smaller schema (`permissionMode`, `nonInteractivePermissions`, `queueOwnerTtlSeconds`, plus optional bridge/timeout fields).

This host stays Docker-first by policy. Use the containerized CLI and `docker exec`/compose workflows when Docker is healthy, and only fall back to the rootless OCI bundle path when Docker layer extraction is blocked by host UID/GID mapping.
The control-plane jobs default to `~/openclaw-workspace` as the active host workspace and, when Docker is temporarily unavailable, they continue the local snapshot/workflow steps while logging a clear warning instead of aborting the whole cycle.

### 1) Build the image (legacy builder only)
```bash
DOCKER_BUILDKIT=0 docker build --build-arg OPENCLAW_VERSION=latest -t openclaw-secure:latest .
```
If the host cannot pull base layers because rootless Docker lacks the needed UID/GID mapping, use the rootless OCI bundle fallback:
```bash
./scripts/update_runc_bundle.sh
```
That path validates the current stable release without depending on Docker image extraction.

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
`scripts/update.sh` now checks whether `openclaw-auto` already exists before trying to create it, and it runs `openclaw doctor --fix` before the final validation/health pass, so routine updates stay quieter and safer. The current stable release target is `2026.4.24`.

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
- `./scripts/update_runc_bundle.sh` rootless OCI fallback when Docker image pulls are blocked by host UID/GID mapping
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
- `./scripts/agentos.py` Agent OS control-plane primitives (queue, events, intake, preflight, scheduler, Telegram envelope)
- `./scripts/channel_intake_bridge.py` normalize external channel JSON into the canonical intake path
- `./scripts/telegram_channel_bridge.py` poll Telegram channel logs and feed inbound updates into the canonical intake path
- `./scripts/before_agent_reply.py` normalize outbound replies and alerts before they leave OpenClaw
- `tools/weekly_blocker_capture_workflow.py` run the weekly finance/legal capture and commit/push the resulting snapshots
- `scripts/finance_export_autowire.py` discover a real finance export, wire the canonical drop-in, and republish the capture when a source appears
- `control-plane/scripts/*.sh` thin wrappers for Agent OS DB init, schema validation, preflight, supervisor cycle, and autonomy snapshots; the autonomy snapshot now emits a ranked top-5 action queue, tracks board-issue changes and packet coverage, and prefers repo-recovery when yellow/stale signals are present
- `control-plane/config/workflow_registry.json` low-risk workflow registry for Green rollout
- `control-plane/scripts/install_prod_weekly_blocker_capture_cron.sh` install the weekly finance/legal capture cron block
- `control-plane/scripts/install_prod_finance_export_autowire_cron.sh` install the finance-export autowire cron block
- `control-plane/scripts/run_workflow.sh` execute one registered low-risk workflow via Agent OS
- Canonical local drop-in path for a finance export: `~/openclaw/data/finance/ledger.csv` (or set `OPENCLAW_LEDGER_EXPORT_PATH`)
- `scripts/finance_export_discovery.py` suggests likely finance export sources from local files when the canonical export is still missing; it now scans common workspaces, Windows user profile roots, and `OneDrive`-style finance folders by default, and you can still extend the scan with `OPENCLAW_LEDGER_EXPORT_SEARCH_PATHS` or widen depth with `OPENCLAW_LEDGER_EXPORT_MAX_DEPTH`
- `scripts/ledger_export_watchdog.py` watch the canonical finance export and alert on appearance/change/disappearance
- `scripts/finance_export_autowire.py` discover a real finance export, wire it into the canonical path, and rerun the weekly capture when a source is found
- `scripts/install_finance_export_dropin.sh` link or copy a real finance export into the canonical drop-in path; workbook sources (`.xlsx` / `.xlsm`) are converted into the canonical `ledger.csv`
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
- the observe cycles also refresh CI, repository progress, and autonomy snapshots on the same cadence; the autonomy snapshot is now a ranked action queue rather than a single CTA.

## Ops checklist
See `CHECKLIST.md`.

## Optional alerts
- `./scripts/healthcheck_notify.sh` will send a Telegram alert if
  `ALERT_TELEGRAM_TARGET` is set.
- `./scripts/ledger_export_watchdog.py` will alert when the canonical finance export appears, changes, or disappears.
- `./scripts/finance_export_autowire.py` will discover a real finance export, wire the canonical drop-in, and rerun the weekly capture when a source is found.
- `./scripts/finance_export_discovery.py --human` will print the best local finance export suggestion, if one exists.
- `./scripts/install_finance_export_dropin.sh /path/to/real-ledger-export.xlsx` will wire a real export into the canonical finance path; workbook sources are converted into `ledger.csv`.
- See `cron/cron.example` for sample scheduling.
