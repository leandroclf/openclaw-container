# OpenClaw Replication Runbook (WSL + Docker)

This runbook documents the exact setup applied on this host, so it can be
reproduced on another machine with the same behavior.

## 1) Target state
- OpenClaw runs in Docker 24/7 with `--restart unless-stopped`.
- Hardened container: `--read-only`, `--cap-drop ALL`, `--tmpfs /tmp`.
- Gateway bound to loopback only on port `18789`.
- Persistent data/logs on host under `~/openclaw`.
- Host-side AgentOS/control-plane snapshots use `~/openclaw-workspace` as the active workspace root.
- Telegram channel enabled with pairing + allowlist.
- Telegram intake is mirrored into Agent OS via `./scripts/telegram_channel_bridge.py`, which polls Telegram logs and forwards inbound updates into the canonical intake queue.
- Daily auto-update to stable (`openclaw@latest`) via cron.

## 2) Host prerequisites
- Ubuntu 24.04 on WSL2.
- Docker Engine working for your user.
- `cron` active in WSL:
  - `service cron status`
  - `systemctl is-enabled cron`
- `git`, `node`, `npm` available on host.

## 3) Clone repo and create directories
```bash
git clone git@github.com:leandroclf/openclaw-container.git ~/openclaw-container
cd ~/openclaw-container

mkdir -p ~/openclaw/{data,logs,config,runtime}
mkdir -p ~/openclaw/runtime/gemini
mkdir -p ~/clawd
chmod 700 ~/openclaw ~/openclaw/data ~/openclaw/runtime
```

## 4) Create secrets file
```bash
cp .env.example ~/openclaw/.env
chmod 600 ~/openclaw/.env
```
Fill `~/openclaw/.env` with real values (never commit this file):
- `TELEGRAM_BOT_TOKEN`
- `OPENCLAW_GATEWAY_TOKEN`
- `BRAVE_API_KEY`
- `OPENAI_IMAGE_GEN_API_KEY`
- `OPENAI_WHISPER_API_KEY`
- `NOTION_API_KEY`
- Optional (feature-dependent): `OPENAI_API_KEY`, `GH_TOKEN`, `GITHUB_TOKEN`

## 5) Build and validate image (legacy builder only)
```bash
cd ~/openclaw-container
DOCKER_BUILDKIT=0 docker build --build-arg OPENCLAW_VERSION=latest -t openclaw-secure:latest .
docker images | rg openclaw-secure
docker run --rm openclaw-secure --version
docker run --rm openclaw-secure gateway --help
```

## 6) Start hardened container
```bash
docker rm -f openclaw 2>/dev/null || true
docker run -d --name openclaw --restart unless-stopped \
  --env-file ~/openclaw/.env \
  --read-only --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v ~/openclaw/data:/home/node/.openclaw-prod \
  -v ~/openclaw/runtime:/home/node/.openclaw \
  -v ~/openclaw/runtime/gemini:/home/node/.gemini \
  -v ~/openclaw/logs:/tmp/openclaw \
  -v ~/clawd:/home/node/clawd \
  openclaw-secure --profile prod gateway run --bind loopback --port 18789
```

## 7) Apply baseline config
Run these commands once:
```bash
docker exec openclaw openclaw --profile prod config set browser.executablePath /usr/bin/chromium
docker exec openclaw openclaw --profile prod config set agents.defaults.workspace /home/node/clawd
docker exec openclaw openclaw --profile prod config set gateway.mode local
docker exec openclaw openclaw --profile prod config set gateway.bind loopback
docker exec openclaw openclaw --profile prod config set gateway.port 18789
docker exec openclaw openclaw --profile prod config set gateway.auth.mode token
docker exec openclaw openclaw --profile prod config set gateway.auth.token '${OPENCLAW_GATEWAY_TOKEN}'
docker exec openclaw openclaw --profile prod config set channels.telegram.enabled true
docker exec openclaw openclaw --profile prod config set channels.telegram.dmPolicy pairing
docker exec openclaw openclaw --profile prod config set channels.telegram.groupPolicy allowlist
docker exec openclaw openclaw --profile prod config set channels.telegram.allowFrom '[343551192]'
docker exec openclaw openclaw --profile prod config set channels.telegram.botToken '${TELEGRAM_BOT_TOKEN}'
docker exec openclaw openclaw --profile prod config set agents.defaults.model.primary google-gemini-cli/gemini-2.5-flash
docker exec openclaw openclaw --profile prod config set agents.defaults.model.fallbacks '["google-gemini-cli/gemini-2.5-pro","anthropic/claude-sonnet-4-5","openai-codex/gpt-5.3-codex"]'
```
Canonical note:
- `~/openclaw/data/openclaw.json` is the runtime source of truth.
- `~/openclaw/config/config.yaml` may lag behind the live runtime; if it is
  used operationally, synchronize it explicitly before rollout.

## 8) Configure OpenAI Codex OAuth
```bash
docker exec -it openclaw openclaw --profile prod onboard --auth-choice openai-codex
docker exec openclaw openclaw --profile prod models status
```
If callback is not captured automatically in WSL, paste the callback URL from
the browser into the terminal prompt.

## 9) Configure Telegram pairing + allowlist
Discover IDs:
```bash
docker exec openclaw openclaw --profile prod directory peers list --channel telegram
docker exec openclaw openclaw --profile prod directory groups list --channel telegram
```
Approve pairing requests:
```bash
docker exec openclaw openclaw --profile prod pairing list
docker exec openclaw openclaw --profile prod pairing approve telegram <PAIRING_CODE>
```
Reapply allowlist if needed:
```bash
docker exec openclaw openclaw --profile prod config set channels.telegram.allowFrom '[343551192]'
```

## 10) Mirror Telegram intake into Agent OS
The runtime keeps Telegram as a channel of record, and the host bridge mirrors
inbound Telegram updates into the Agent OS intake queue on the observe cycle.
This is wired through the `telegram_channel_ingest` workflow in
`control-plane/config/workflow_registry.json`.

Manual dry-run:
```bash
./scripts/telegram_channel_bridge.py --dry-run
```

## 11) Install real cron schedule in WSL
Create alert target file:
```bash
cat > ~/openclaw/config/alerts.env <<'EOF'
ALERT_TELEGRAM_TARGET=343551192
EOF
chmod 600 ~/openclaw/config/alerts.env
```
Install cron block:
```bash
cd ~/openclaw-container
./scripts/install_cron.sh
./control-plane/scripts/install_prod_weekly_blocker_capture_cron.sh
crontab -l
```
Canonical local drop-in path for a finance export:
```bash
~/openclaw/data/finance/ledger.csv
```
Installed schedules:
- `*/15 * * * *` healthcheck + optional Telegram alert.
- `0 3 * * 0` weekly backup.
- `30 3 * * *` daily rebuild/restart/update.
- `45 3 * * *` model routing baseline (`cost_optimized`) after update.
- `5 8 * * 1-5` model routing for business hours (`balanced_default`).
- `5 20 * * *` model routing for off-hours (`cost_optimized`).
- `15 4 * * *` log pruning/compression.
- `17,47 * * * *` observe cycle refreshes CI, repo progress, and autonomy snapshots. The snapshot now surfaces a top-5 next-action queue, board-issue changes, packet coverage, and the ISSUE-007 CI gate progress; it should favor repo-recovery whenever yellow/stale signals appear.
- `15 7 * * 0` weekly finance/legal capture, which runs the weekly blocker workflow and commits/pushes the dated snapshots when they change.

To avoid duplicated health routines between WSL cron and OpenClaw internal
scheduler, disable the two internal health jobs once:
```bash
docker exec openclaw openclaw --profile prod cron disable f257b81c-d28b-48b5-af72-e02512f99cfb
docker exec openclaw openclaw --profile prod cron disable 32a75901-b0b1-4b72-8153-12a9e44beee9
```

## 12) Verification commands
```bash
docker ps --filter name=openclaw
docker exec openclaw openclaw --profile prod gateway health
docker exec openclaw openclaw --profile prod status
tail -n 200 ~/openclaw/logs/openclaw-$(date +%F).log
```

## 13) Stable update policy
- `scripts/update.sh` resolves the newest `openclaw` npm stable version and
  passes it as `OPENCLAW_VERSION` build arg.
- `latest` is the stable channel.
- To check tags:
```bash
npm view openclaw dist-tags --json
```
`beta` can be newer than `latest`; this setup intentionally follows `latest`
for stability.

### 12.1) Efficiency upgrades from 2026.4.2
- Treat Task Flow and child-task metadata as first-class. Every new wave should record a parent task, child tasks, and a replay key when it fans out.
- Keep the session/replay source metadata on every inbound request. That is what lets Telegram, Slack, Discord, WhatsApp, cron, and board inputs collapse into one canonical packet.
- Use `before_agent_reply` to normalize outbound replies before they leave the system. That keeps approval messages and operational alerts consistent across channels.
- Keep `openclaw doctor --fix` in the update path. It now closes the most common config/layout drift before health checks run.
- Use the weekly finance/legal capture workflow so ISSUE-011 and ISSUE-012 stay reproducible and auto-published.
- Use `/v1/models` and `/v1/embeddings` when integrating tools that expect OpenAI-compatible discovery or embedding endpoints.
- Treat the Control UI tool visibility as the fastest way to decide whether to ask the agent for code, research, or a different specialist.

Policy note:
- This environment stays Docker-only. Do not install or rely on a host-side OpenClaw CLI for privileged operations; keep access centralized in the container and use `docker exec`, compose, or container-managed scripts.

## 14) Change alert target to another Telegram user/chat
1. Set new ID in `~/openclaw/config/alerts.env`:
   - `ALERT_TELEGRAM_TARGET=<new_user_or_chat_id>`
2. Validate send path:
```bash
. ~/openclaw/config/alerts.env && /home/leandro/openclaw-container/scripts/healthcheck_notify.sh
```
3. If target is a group/channel, ensure OpenClaw can address it (allowlist and
pairing policy as required by your channel config).

## 15) Optional host tool alignment (Codex + Claude + VS Code)
```bash
# WSL Codex CLI
npm install -g --prefix ~/.local @openai/codex@latest
codex --version

# WSL Claude CLI (stable)
# If "claude install stable" hangs in this host/TTY, use npm update directly.
npm install -g --prefix ~/.local @anthropic-ai/claude-code@latest
claude -v
npm view @anthropic-ai/claude-code version

# VS Code extension from WSL
"/mnt/c/Users/<WINDOWS_USER>/AppData/Local/Programs/Microsoft VS Code/bin/code" \
  --install-extension openai.chatgpt --force
```

OpenClaw remains Docker-only in this environment. Use `docker exec` against the
running container and keep privileged access centralized there.

## 16) Objective-based model routing (quality + cost)
Routing policy and scores:
- `ops/model-routing/model_catalog.json`
- `ops/model-routing/objectives.json`

Commands:
```bash
cd ~/openclaw-container
./scripts/model_router.py --list-objectives
./scripts/model_router.py --objective balanced_default
./scripts/model_router.py --objective coding_quality --apply --run-callbacks
```

Suggested default objective:
- `balanced_default` for daily operation.

Suggested specialized objectives:
- `coding_quality` for deep implementation/debug.
- `reasoning_quality` for planning/architecture.
- `research_depth` for synthesis and benchmarking.
- `cost_optimized` for recurring automation and cron jobs.

## 16) Zero-downtime upgrade path (mandatory for future changes)

Do not apply risky changes directly on production container `openclaw`.
Use parallel candidate validation with `openclaw-next`.
Keep candidate workspace isolated in `~/clawd-next`.

Reference docs:
- `docs/operations/PRODUCTION_CHANGE_POLICY.md`
- `docs/operations/BLUE_GREEN_WSL_DOCKER_DESKTOP.md`
- `docs/operations/TEST_STRATEGY.md`

Mandatory checks before any stop/rm/run command:
```bash
docker context ls
docker context show
docker ps --filter name=openclaw
docker exec openclaw openclaw --profile prod gateway health
```

Only promote candidate after functional tests and soak window succeed.
Run automated gates before promotion:
```bash
./scripts/test_gate.sh --with-integration
```

## 17) Optional compose blue/green templates

Templates are available for controlled migration to compose-managed workflows:
- `compose/docker-compose.blue-green.yml`
- `compose/blue.env.example`
- `compose/green.env.example`

Usage and safety guide:
- `docs/operations/COMPOSE_BLUE_GREEN_USAGE.md`

Do not use compose `blue` profile on production unless migration is planned and
rollback is ready.
