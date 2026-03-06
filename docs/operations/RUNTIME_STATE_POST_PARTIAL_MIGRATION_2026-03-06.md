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

### Agent OS production policy audit

- `19,49 * * * *` -> `control-plane/scripts/prod_policy_audit_cycle.sh`

### Agent OS production autopilot SLA

- `45 22 * * *` -> `control-plane/scripts/prod_autopilot_sla_cycle.sh`

Removed from host cron during cleanup:

- obsolete Green observe block
- redundant host-side `tools/github_ci_status.py` line

## OpenClaw internal cron (current)

Enabled internal jobs:

- `Autopilot sequential delivery cycle`
- `Autopilot idle watchdog`
- `Daily summary rotation`
- `Weekly code evolution KPI audit`
- `Weekly specialist productivity audit`

Disabled internal jobs:

- `Daily ops state lint`
- `Daily autopilot SLA tracker`

## Agent OS slice active in production

### Current scope

The active production Agent OS lane is `observe-only`.

It currently runs:

- `daily_ops_state_lint`
- `product_progress_snapshot`
- `github_ci_status_collect`

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

## Agent OS policy wrapper slice in production

### Current scope

The deploy-audit policy layer also runs host-side now.

It currently runs:

- `deploy_audit_policy_wrapper.py`

It consumes only:

- `deploy-status.json`
- `ci-regression-watchdog.json`
- `product-code-progress.json`

It does not run:

- `github_ci_status.py`
- `product_progress_snapshot.py`
- direct GitHub collection

### Runtime state

- log:
  - `~/openclaw/logs/agentos-prod-policy-audit.log`
- lock:
  - `~/openclaw/runtime/agentos/prod-policy-audit.lock`

## Ownership model after cleanup

### Host-side WSL cron owns

- health/recovery alerts
- maintenance and audits
- backup/update/log pruning
- model routing refresh
- Agent OS `prod-observe`
- Agent OS `prod-policy-audit`
- Agent OS `prod-autopilot-sla`

### OpenClaw internal cron owns

- delivery autopilot
- idle watchdog
- daily summary rotation
- weekly governance/KPI audits

### Agent OS `prod-observe` owns

- structured observation of low-risk operational workflows
- append-only DB/event/report evidence
- host-side production observation cadence
- collection of CI/progress artifacts used by policy evaluation

### Agent OS `prod-policy-audit` owns

- freshness validation for collection artifacts
- `ALERT_OWNERSHIP_POLICY.md` evaluation
- `daily-summary.md` policy append
- host-side production policy cadence

### Agent OS `prod-autopilot-sla` owns

- deterministic SLA generation from workspace telemetry
- `autopilot-sla.json` and `autopilot-sla.md` refresh
- dashboard sync for SLA artifacts
- host-side production SLA cadence

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
- operationally replaced and disabled:
  - internal `Deploy log capture and status audit`
  - internal `Daily autopilot SLA tracker`

## Recommended next phase

The next phase should not be another broad migration wave.

It should be a targeted migration pass for:

1. autopilot ownership boundaries
2. whether any non-observe workflow should enter Agent OS beyond deterministic file-based jobs
3. whether the idle watchdog can be decomposed into deterministic observation + agent execution lanes

Until that redesign exists, the current state is coherent and should remain stable.
