# Agent OS Green Scheduled Observation

Purpose: run the validated low-risk Agent OS workflows on `openclaw-next` only, using WSL cron as the host-side scheduler, without changing production (`openclaw`) cron behavior.

## Scope

This scheduled observation runs these workflows against `~/clawd-next`:

- `daily_ops_state_lint`
- `daily_summary_rotation`
- `product_progress_snapshot`

It writes state to:

- SQLite DB: `~/openclaw-next/runtime/agentos/green-observe.db`
- Log file: `~/openclaw-next/logs/agentos-green-observe.log`

## Install

```bash
/home/leandro/openclaw-container/control-plane/scripts/install_green_observe_cron.sh
```

Default schedule:

- `12,32,52 * * * *`

This keeps the candidate observation independent from the production cron block.

## Manual dry run

```bash
/home/leandro/openclaw-container/control-plane/scripts/green_observe_cycle.sh
```

## Safety properties

- Uses `openclaw-next` only.
- Uses `~/clawd-next` only.
- Does not send Telegram from the candidate.
- Uses a dedicated lock file via `flock` to avoid overlap.
- Keeps WSL cron as the source of truth for host scheduling.

## Verification

```bash
crontab -l
tail -n 200 ~/openclaw-next/logs/agentos-green-observe.log
docker exec openclaw-next openclaw --profile prod gateway health
```

## Rollback

Remove only the managed Green block:

```bash
crontab -l | sed '/^# === OpenClaw Agent OS Green observe ===$/,/^# === \\/OpenClaw Agent OS Green observe ===$/d' | crontab -
```

This does not modify the production OpenClaw cron block.
