# Agent OS Prod Idle Watchdog Policy Prep - 2026-03-06

## Scope

Prepare the second host-side migration cut for `Autopilot idle watchdog`: deterministic policy evaluation only, without triggering mini-cycles from the host.

## What was added

- `scripts/idle_watchdog_policy_wrapper.py`
- `control-plane/scripts/prod_idle_watchdog_policy_cycle.sh`
- `control-plane/scripts/install_prod_idle_watchdog_policy_cron.sh`

## Manual validation

Executed:

- `/home/leandro/openclaw-container/control-plane/scripts/prod_idle_watchdog_policy_cycle.sh`

Observed:

- pre-run `Gateway Health OK`
- wrapper consumed fresh `watchdog-monitor.json`
- appended deterministic block to `daily-summary.md`
- post-run `Gateway Health OK`

Observed wrapper output:

```text
[WATCHDOG_REQUEST_HANDOFF]
```

## Daily summary evidence

The wrapper appended:

- `## Daily Summary - 2026-03-06 15:10 UTC`

Recorded decision:

- `Decision: REQUEST_MINI_CYCLE_HANDOFF`
- `Suggested Action (source): TRIGGER_MINI_CYCLE`
- `Next Action: Registrar o pedido de handoff; nao disparar mini-cycle pelo host-side nesta fase.`

## Host cron block

Installed in production:

```cron
# === OpenClaw Agent OS Prod idle watchdog policy ===
9 * * * * flock -n /home/leandro/openclaw/runtime/agentos/prod-idle-watchdog-policy.lock /home/leandro/openclaw-container/control-plane/scripts/prod_idle_watchdog_policy_cycle.sh >> /home/leandro/openclaw/logs/agentos-prod-idle-watchdog-policy.log 2>&1
# === /OpenClaw Agent OS Prod idle watchdog policy ===
```

## Important constraint

This policy slice still does **not**:

- execute the mini-cycle from host-side cron
- replace the internal `Autopilot idle watchdog`
- interact with Telegram

It only records the deterministic handoff decision.

## Next gate

Observe at least one automatic run of:

- `prod-idle-watchdog-observe`
- `prod-idle-watchdog-policy`

Then decide whether the internal `Autopilot idle watchdog` can be reduced or whether a handoff bridge is needed first.
