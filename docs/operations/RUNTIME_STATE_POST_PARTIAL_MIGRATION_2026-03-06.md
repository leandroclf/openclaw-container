# Runtime State Post Partial Migration - 2026-03-06

Purpose: capture the current steady-state runtime after the partial Agent OS migration and cleanup work already applied.

## Production runtime

- Active container:
  - `openclaw`
- Removed:
  - `openclaw-next`
  - `~/openclaw-next`
  - `~/clawd-next`
- Production health at documentation time:
  - `Gateway Health OK`
  - `Telegram: ok (@StephenFryBot)`

## Host-side WSL cron (current)

Active host scheduler blocks:

### OpenClaw container ops

- `*/15 * * * *` -> `scripts/healthcheck_notify.sh`
- `10 6 * * *` -> `scripts/daily_maintenance.sh`
- `0 3 * * 0` -> `scripts/backup.sh`
- `30 3 * * *` -> `scripts/update.sh`
- `45 3 * * *` -> `scripts/model_router.py --objective balanced_default --probe --apply`
- `5 8 * * 1-5` -> `scripts/model_router.py --objective balanced_default --probe --apply`
- `5 20 * * *` -> `scripts/model_router.py --objective cost_optimized --probe --apply`
- `15 4 * * *` -> `scripts/prune_logs.sh`

### Agent OS production observe

- `17,47 * * * *` -> `control-plane/scripts/prod_observe_cycle.sh`

Removed from host cron during cleanup:

- obsolete Green observe block
- redundant host-side `tools/github_ci_status.py` line

## OpenClaw internal cron (current)

Enabled internal jobs:

- `Autopilot sequential delivery cycle`
- `Autopilot idle watchdog`
- `Deploy log capture and status audit`
- `Daily autopilot SLA tracker`
- `Daily summary rotation`
- `Weekly code evolution KPI audit`
- `Weekly specialist productivity audit`

Disabled internal jobs:

- `Daily ops state lint`

## Agent OS slice active in production

### Current scope

The active production Agent OS lane is `observe-only`.

It currently runs:

- `daily_ops_state_lint`
- `product_progress_snapshot`

It no longer runs:

- `daily_summary_rotation`

Reason:

- rotation remains owned by the internal once-daily OpenClaw cron
- Agent OS execution of that workflow was only producing `no-rotation-needed`

### Runtime state

- DB:
  - `~/openclaw/runtime/agentos/prod-observe.db`
- log:
  - `~/openclaw/logs/agentos-prod-observe.log`
- lock:
  - `~/openclaw/runtime/agentos/prod-observe.lock`

## Ownership model after cleanup

### Host-side WSL cron owns

- health/recovery alerts
- maintenance and audits
- backup/update/log pruning
- model routing refresh
- Agent OS `prod-observe`

### OpenClaw internal cron owns

- delivery autopilot
- idle watchdog
- CI/deploy audit with alert policy
- daily summary rotation
- weekly governance/KPI audits

### Agent OS `prod-observe` owns

- structured observation of low-risk operational workflows
- append-only DB/event/report evidence
- host-side production observation cadence

## What was intentionally not migrated yet

- Telegram delivery behavior
- writeback/commit/push workflows
- CI remediation ownership
- internal autopilot replacement
- weekly governance jobs

## Current migration boundary

The system is now in a hybrid steady state:

- production is running on the hardened `openclaw` container
- Agent OS is active only as a low-risk observation lane
- legacy internal cron remains for delivery/governance behaviors
- duplicate/stale schedulers already removed:
  - Green observe host block
  - host-side standalone `github_ci_status.py`
  - internal `Daily ops state lint`

## Recommended next phase

The next phase should not be another broad migration wave.

It should be a targeted design pass for:

1. `Deploy log capture and status audit`
2. autopilot ownership boundaries
3. whether any non-observe workflow should enter Agent OS

Until that redesign exists, the current state is coherent and should remain stable.
