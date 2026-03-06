# Cron Cleanup Analysis - 2026-03-06

Purpose: identify which legacy schedulers are still necessary after enabling the Agent OS `prod-observe` slice, and which ones are now overlapping or redundant.

## Current scheduler layers

### Host-side WSL cron

Current `crontab -l` blocks:

- `*/15 * * * *` -> `scripts/healthcheck_notify.sh`
- `10 6 * * *` -> `scripts/daily_maintenance.sh`
- `0 3 * * 0` -> `scripts/backup.sh`
- `30 3 * * *` -> `scripts/update.sh`
- `45 3 * * *` -> `scripts/model_router.py --objective balanced_default --probe --apply`
- `5 8 * * 1-5` -> `scripts/model_router.py --objective balanced_default --probe --apply`
- `5 20 * * *` -> `scripts/model_router.py --objective cost_optimized --probe --apply`
- `15 4 * * *` -> `scripts/prune_logs.sh`
- `20 7 * * *` -> `python3 tools/github_ci_status.py`
- `12,32,52 * * * *` -> `green_observe_cycle.sh` (now obsolete because Green was removed)
- `17,47 * * * *` -> `prod_observe_cycle.sh`

### OpenClaw internal cron

`openclaw --profile prod cron list --json` currently shows:

- `Autopilot sequential delivery cycle`
- `Autopilot idle watchdog`
- `Deploy log capture and status audit`
- `Daily autopilot SLA tracker`
- `Daily summary rotation`
- `Daily ops state lint`
- `Weekly code evolution KPI audit`
- `Weekly specialist productivity audit`

## What `prod-observe` now covers

The production Agent OS observation slice runs these workflows:

- `daily_ops_state_lint`
- `daily_summary_rotation`
- `product_progress_snapshot`

This means it overlaps functionally with:

- internal `Daily summary rotation`
- internal `Daily ops state lint`
- part of internal `Deploy log capture and status audit` (the `product_progress_snapshot.py` portion only)

## Jobs that should remain unchanged

These jobs still have distinct responsibility and should stay active for now:

### Keep: host-side WSL cron

- `healthcheck_notify.sh`
  - host/container health gate + Telegram alerting
- `daily_maintenance.sh`
  - runtime validation, placeholder audit, conflict checks, optional recovery
- `backup.sh`
  - backup policy
- `update.sh`
  - image/runtime refresh
- `model_router.py` schedules
  - routing policy application, not covered by Agent OS observe
- `prune_logs.sh`
  - filesystem hygiene
- `tools/github_ci_status.py`
  - CI/deploy audit, not replaced by `prod-observe`

### Keep: OpenClaw internal cron

- `Autopilot sequential delivery cycle`
  - delivery behavior, not replaced
- `Autopilot idle watchdog`
  - continuity/watchdog logic, not replaced
- `Daily autopilot SLA tracker`
  - SLA reporting, not replaced
- `Weekly code evolution KPI audit`
  - weekly KPI audit, not replaced
- `Weekly specialist productivity audit`
  - weekly governance/reporting, not replaced

## Jobs now overlapping

### Overlap 1: `Daily ops state lint`

- Internal cron:
  - `Daily ops state lint` at `23:30`
- Agent OS `prod-observe`:
  - every hour at `17` and `47`

Assessment:

- Safe candidate for removal from internal cron.
- The Agent OS path now exercises the same underlying script with better artifact/DB tracking.

### Overlap 2: `Daily summary rotation`

- Internal cron:
  - `Daily summary rotation` at `23:10`
- Agent OS `prod-observe`:
  - every hour at `17` and `47`

Assessment:

- Overlap exists, but this one needs more care.
- The original internal cron runs once daily, which matches the semantic intent of rotation.
- The Agent OS lane currently runs the rotation script much more frequently; it has been harmless so far because the script reports `no-rotation-needed`, but this is still semantic duplication.

Recommendation:

- Do **not** disable the internal daily summary rotation yet.
- First either:
  1. move `daily_summary_rotation` out of `prod-observe`, or
  2. create a dedicated lower-frequency Agent OS schedule for that workflow.

### Overlap 3: `Deploy log capture and status audit`

Internal job payload:

- runs `python3 tools/github_ci_status.py`
- runs `python3 ops/multiagent/delivery/scripts/product_progress_snapshot.py`

Overlap with `prod-observe`:

- `product_progress_snapshot.py` is now duplicated

Assessment:

- Partial overlap only.
- The internal job also applies alert ownership policy and records daily-summary evidence, which `prod-observe` does not replace.

Recommendation:

- Keep this internal cron active for now.
- If cleanup is desired later, split its responsibilities first:
  - move `github_ci_status.py` + alert ownership to a host-side Agent OS or WSL cron path
  - then retire the internal job

## Green cleanup note

The Green scheduler block is now obsolete because:

- `openclaw-next` was removed
- `~/openclaw-next` was removed
- `~/clawd-next` was removed

Current risk:

- the Green block still exists in `crontab -l` and points to paths that no longer exist

Impact:

- harmless in terms of production runtime
- noisy operationally, because it can generate recurring cron errors

## Recommended cleanup order

### Step 1 — safe immediate cleanup

Remove the obsolete Green cron block from host `crontab`.

Reason:

- zero value
- stale paths
- no production dependency

### Step 2 — safe next cleanup

Disable the internal OpenClaw cron job:

- `Daily ops state lint`

Reason:

- fully covered by `prod-observe`
- low-risk duplication

### Step 3 — defer until scheduling is refactored

Do not disable yet:

- internal `Daily summary rotation`
- internal `Deploy log capture and status audit`

Reason:

- both still carry behavior not yet cleanly re-homed

## Final recommendation

At this point, the safest cleanup is:

1. remove the obsolete Green host cron block
2. keep `prod-observe` active
3. disable only internal `Daily ops state lint`
4. leave `Daily summary rotation` and `Deploy log capture and status audit` unchanged until their scheduling/ownership is redesigned

This avoids breaking production behavior while still reducing one confirmed duplicate path and one stale scheduler block.
