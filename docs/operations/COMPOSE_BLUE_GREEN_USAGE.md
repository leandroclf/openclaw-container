# Compose Blue/Green Usage

This file explains how to use compose templates safely without impacting
production.

## Files

- `compose/docker-compose.blue-green.yml`
- `compose/blue.env.example`
- `compose/green.env.example`

## Safety rules

- Do not run `blue` profile on hosts where production `openclaw` is already
  managed outside compose, unless you are explicitly migrating management mode.
- Use `green` profile for candidate validation first.
- Always confirm Docker context before compose commands.
- This host currently uses `docker-compose` (v1). If your host has Compose v2,
  you can replace `docker-compose` with `docker compose`.

## Recommended flow (candidate only)

1. Create candidate env file:

```bash
cp compose/green.env.example compose/green.env
```

Edit `compose/green.env` and set:
- `GREEN_RUNTIME_ENV_FILE=/home/leandro/openclaw-next/.env`

2. Start Green profile:

```bash
docker-compose -f compose/docker-compose.blue-green.yml \
  --env-file compose/green.env \
  --profile green up -d
```

3. Validate candidate:

```bash
docker ps --filter name=openclaw-next
docker exec openclaw-next openclaw --profile prod gateway health
docker exec openclaw-next openclaw --profile prod status
./scripts/test_gate.sh --with-integration
```

4. Stop candidate when done:

```bash
docker-compose -f compose/docker-compose.blue-green.yml \
  --env-file compose/green.env \
  --profile green down
```

## Optional full compose-managed mode

When you decide to manage Blue with compose too:

```bash
cp compose/blue.env.example compose/blue.env
```

Edit `compose/blue.env` and set:
- `BLUE_RUNTIME_ENV_FILE=/home/leandro/openclaw/.env`

```bash
docker-compose -f compose/docker-compose.blue-green.yml \
  --env-file compose/blue.env \
  --profile blue up -d
```

Use this only after explicit maintenance planning and rollback readiness.
