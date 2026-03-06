# Agent OS Prod Idle Watchdog Observe Prep - 2026-03-06

## Scope

Prepare the first host-side migration cut for `Autopilot idle watchdog` as observation only, without moving mini-cycle execution out of OpenClaw.

## What was added

- `scripts/idle_watchdog_observer.py`
- `control-plane/scripts/prod_idle_watchdog_observe_cycle.sh`
- `control-plane/scripts/install_prod_idle_watchdog_observe_cron.sh`

## Manual validation

Executed:

- `/home/leandro/openclaw-container/control-plane/scripts/prod_idle_watchdog_observe_cycle.sh`

Observed:

- pre-run `Gateway Health OK`
- `watchdog-monitor.json` generated
- `watchdog-monitor.md` generated
- post-run `Gateway Health OK`

Generated artifacts:

- `/home/leandro/clawd/ops/multiagent/delivery/watchdog-monitor.json`
- `/home/leandro/clawd/ops/multiagent/delivery/watchdog-monitor.md`

Observed decision snapshot:

- `suggested_action: TRIGGER_MINI_CYCLE`
- `active_blockers_detected: false`
- `productive_advancement_detected: false`
- `eligible_auto_tasks: 6`

## Host cron block

Installed in production as observation only:

```cron
# === OpenClaw Agent OS Prod idle watchdog observe ===
7 * * * * flock -n /home/leandro/openclaw/runtime/agentos/prod-idle-watchdog-observe.lock /home/leandro/openclaw-container/control-plane/scripts/prod_idle_watchdog_observe_cycle.sh >> /home/leandro/openclaw/logs/agentos-prod-idle-watchdog-observe.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog observe ===
```

## Important constraint

This first cut does **not**:

- trigger mini-cycles from host-side cron
- send Telegram messages
- replace the internal `Autopilot idle watchdog`

It only captures deterministic observation artifacts.

## Production safety

Validated after installation:

- `docker exec openclaw openclaw --profile prod gateway health`
- Result: `Gateway Health OK`, `Telegram ok`

## Next gate

Observe the first scheduled host-side run, verify `watchdog-monitor.json/.md` freshness and log stability, then decide whether to add a host-side watchdog policy wrapper before touching the internal watchdog cron.
