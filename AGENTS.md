# OpenClaw Container (WSL) - Codex Operating Guide

Goal: keep OpenClaw running 24/7 in Docker on WSL (Ubuntu-24.04) with
hardening enabled, stable health, and clear operational procedures.

## Non-negotiables
- Always run commands in WSL (Ubuntu), never PowerShell.
- Do **not** use BuildKit/buildx. Use legacy build:
  `DOCKER_BUILDKIT=0 docker build ...`
- One command at a time. Verify with `docker ps`, `docker images`, `ls`.
- Never print secrets (tokens/keys). If logs show them, mask.
- Do not remove containers unless explicitly needed to fix issues.
- Keep gateway bind on loopback only.

## Repo layout
- Dockerfile lives at repo root: `/home/leandro/openclaw-container/Dockerfile`.
- Data volume: `~/openclaw/data` -> `/home/node/.openclaw-prod`
- Runtime volume (cron): `~/openclaw/runtime` -> `/home/node/.openclaw`
- Logs: `~/openclaw/logs` -> `/tmp/openclaw`
- Workspace: `~/clawd` -> `/home/node/clawd`

## Build image (legacy builder)
```bash
DOCKER_BUILDKIT=0 docker build -t openclaw-secure:latest .
```
- Dockerfile installs Chromium (headless) and fonts; apt-get uses retries.
- If apt times out, keep legacy builder and re-run.

## Run container (hardened)
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

## Health checks
- `docker ps`
- `docker exec openclaw openclaw --profile prod gateway health`
  - If you see `1006` right after restart, wait 5-10s and retry.

## Logs
- File logs are persisted on host:
  `tail -n 200 ~/openclaw/logs/openclaw-YYYY-MM-DD.log`
- `docker logs` may be empty (OpenClaw writes to file).

## Config management
- Prefer `openclaw config set/get/unset` for changes.
- Config file is on host: `~/openclaw/data/openclaw.json`.
- Avoid creating quoted keys in `skills.entries`.
  - Use unquoted keys (e.g., `skills.entries.openai-image-gen`).

### Current key settings (do not remove)
- `browser.executablePath = /usr/bin/chromium`
- `agents.defaults.workspace = /home/node/clawd`
- `gateway.bind = loopback`, `gateway.mode = local`, `gateway.port = 18789`
- `channels.telegram.dmPolicy = pairing`
- `channels.telegram.groupPolicy = allowlist`
- `channels.telegram.allowFrom = [343551192]`
- Default model: `openai-codex/gpt-5.3-codex`

## Secrets policy
- All secrets live in `~/openclaw/.env` (chmod 600). Do not print.
- Required env keys (names only):
  - `TELEGRAM_BOT_TOKEN`
  - `OPENCLAW_GATEWAY_TOKEN`
  - `BRAVE_API_KEY`
  - `OPENAI_IMAGE_GEN_API_KEY`
  - `OPENAI_WHISPER_API_KEY`
  - `NOTION_API_KEY`
- Config uses `${VAR_NAME}` placeholders for those secrets.

## OAuth (OpenAI Codex)
- Use onboarding wizard (interactive):
  `docker exec -it openclaw openclaw --profile prod onboard --auth-choice openai-codex`
- Callback may require manual paste in WSL.
- Auth store: `/home/node/.openclaw-prod/agents/main/agent/auth-profiles.json`.

## Telegram pairing
- List: `docker exec openclaw openclaw --profile prod pairing list`
- Approve: `docker exec openclaw openclaw --profile prod pairing approve telegram <CODE>`
- Allowlist must stay restricted to user id 343551192.

## Troubleshooting
- If health fails after hardening, check writes to `/home/node/.openclaw`.
- If unauthorized `device_token_mismatch`, ensure gateway token is provided
  via env and config placeholder `${OPENCLAW_GATEWAY_TOKEN}`.
- If container fails, inspect `/tmp/openclaw/openclaw-*.log` (persisted).

## Interaction style for Codex
- Provide short summaries + next steps + risks.
- Ask before destructive actions or production-impacting changes.
- Mask secrets in any output.

## Helper scripts
- `./scripts/update.sh` build + restart + health
- `./scripts/restart.sh` restart + health
- `./scripts/healthcheck.sh` health with retries
- `./scripts/logs.sh` tail latest log (add `--follow`)
- `./scripts/backup.sh` backup core state (credentials excluded by default)
