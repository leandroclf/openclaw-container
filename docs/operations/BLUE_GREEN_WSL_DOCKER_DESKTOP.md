# Blue/Green Deployment on WSL (with optional Docker Desktop)

Use this runbook to deploy a candidate stack in parallel without stopping
current production.

## A) Decide Docker context

```bash
docker context ls
docker context show
```

Choose one context for the full operation.

Examples:
- WSL daemon: `default`
- Docker Desktop daemon: `desktop-linux`

Use explicit context in all commands if needed:

```bash
docker --context desktop-linux ps
```

## B) Prepare Green folders (one-time)

```bash
mkdir -p ~/openclaw-next/{data,runtime,logs,config}
mkdir -p ~/openclaw-next/runtime/gemini
mkdir -p ~/clawd-next
chmod 700 ~/openclaw-next ~/openclaw-next/data ~/openclaw-next/runtime
```

Create candidate env file (never reuse production file directly):

```bash
cp ~/openclaw/.env ~/openclaw-next/.env
chmod 600 ~/openclaw-next/.env
```

Then edit `~/openclaw-next/.env` and set a non-production Telegram token (or
remove Telegram token for candidate test runs).

Prepare isolated workspace copy for Green:

```bash
rsync -a --delete ~/clawd/ ~/clawd-next/
```

## C) Build candidate image

```bash
DOCKER_BUILDKIT=0 docker build -t openclaw-secure:candidate .
```

## D) Run Green container in parallel

```bash
docker rm -f openclaw-next 2>/dev/null || true
docker run -d --name openclaw-next --restart unless-stopped \
  --env-file ~/openclaw-next/.env \
  --read-only --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v ~/openclaw-next/data:/home/node/.openclaw-prod \
  -v ~/openclaw-next/runtime:/home/node/.openclaw \
  -v ~/openclaw-next/runtime/gemini:/home/node/.gemini \
  -v ~/openclaw-next/logs:/tmp/openclaw \
  -v ~/clawd-next:/home/node/clawd \
  openclaw-secure:candidate --profile prod gateway run --bind loopback --port 28789
```

## E) Validate Green functional behavior

```bash
docker ps --filter name=openclaw
docker exec openclaw-next openclaw --profile prod gateway health
docker exec openclaw-next openclaw --profile prod status
tail -n 200 ~/openclaw-next/logs/openclaw-$(date +%F).log
```

Recommended soak window: at least 12h for non-trivial infra changes.

## F) Promote with rollback ready

Only after Green passes all checks.

1. Save Blue state snapshot.
2. Stop Blue and start promoted container on production port.
3. Re-run health and channel checks.

Rollback must be prepared as exact reverse commands.

## G) Docker Desktop notes

- Docker Desktop gives better GUI logs/containers, but can use a different
  daemon/context than WSL default.
- Always confirm `docker context show` before any stop/rm/run command.
- Do not mix contexts in a single rollout session.
