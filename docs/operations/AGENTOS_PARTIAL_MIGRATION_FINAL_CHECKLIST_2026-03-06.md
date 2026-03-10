# Agent OS Partial Migration Final Checklist - 2026-03-06

## Verified Runtime Baseline

- Docker context: `default`
- Production container: `openclaw`
- Gateway health: `OK`
- Telegram channel: `ok (@StephenFryBot)`

## Host-Side Lanes Active in Production

- `prod-observe`
  - cadence: `17,47 * * * *`
  - scope:
    - `daily_ops_state_lint`
    - `product_progress_snapshot`
    - `github_ci_status_collect`
- `prod-policy-audit`
  - cadence: `19,49 * * * *`
  - scope:
    - deploy/CI policy wrapper based on fresh collection artifacts
- `prod-autopilot-sla`
  - cadence: `45 22 * * *`
  - scope:
    - deterministic SLA materialization
- `prod-idle-watchdog-observe`
  - cadence: `7 * * * *`
  - scope:
    - deterministic watchdog observation only
- `prod-idle-watchdog-policy`
  - cadence: `9 * * * *`
  - scope:
    - deterministic watchdog policy summary only

## Internal OpenClaw Cron Still Active

- `Autopilot sequential delivery cycle`
- `Autopilot idle watchdog`
- `Daily summary rotation`
- `Weekly code evolution KPI audit`
- `Weekly specialist productivity audit`

## Internal OpenClaw Cron Removed from Primary Path

- `Daily ops state lint`
- `Deploy log capture and status audit`
- `Daily autopilot SLA tracker`

## Idle Watchdog Migration Status

- observe lane: `active`
- policy lane: `active`
- handoff bridge: `prepared`
- consumer scaffold: `prepared`
- execution bridge: `prepared (dry-run)`
- manual activation helper: `prepared`
- readiness gate: `active`
- executor ownership transfer: `not approved`

## Current Cutover Decision

- readiness result: `NO_GO`
- blocking condition:
  - internal `Autopilot idle watchdog` remains the primary executor

## Operational Meaning

This means the partial migration is stable for:

- collection
- policy evaluation
- deterministic SLA materialization
- deterministic watchdog observation

It is **not** yet complete for:

- watchdog execution ownership transfer
- deactivation of the internal `Autopilot idle watchdog`

## Before Any Further Cutover

Run:

```bash
python3 /home/leandro/openclaw-container/scripts/idle_watchdog_cutover_readiness.py \
  --bridge-dir /home/leandro/openclaw/runtime/agentos/handoffs
```

And only proceed if:

- result is `GO`
- `manual_idle_watchdog_cutover_activate.sh --confirm-cutover` is authorized
- rollback operator is present

## Final Status

- partial migration: `stable`
- production health: `stable`
- further idle-watchdog cutover: `blocked by design`
