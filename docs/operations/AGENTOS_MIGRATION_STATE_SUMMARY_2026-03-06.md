# Agent OS Migration State Summary - 2026-03-06

## Objective

Consolidate the effective production state after the current partial Agent OS migration waves.

## Production state

- container: `openclaw`
- gateway: `OK`
- Telegram: `ok (@StephenFryBot)`
- Docker context: `default`

## Host-side lanes already active

### 1. `prod-observe`

Schedule:

- `17,47 * * * *`

Owns:

- `daily_ops_state_lint`
- `product_progress_snapshot`
- `github_ci_status_collect`

Produces:

- `deploy-status.json/.md`
- `ci-regression-watchdog.json/.md`
- `product-code-progress.json/.md`
- `ops-lint-report.md`

### 2. `prod-policy-audit`

Schedule:

- `19,49 * * * *`

Owns:

- freshness validation for deploy/progress artifacts
- `ALERT_OWNERSHIP_POLICY.md` evaluation
- `daily-summary.md` append for CI/deploy policy

### 3. `prod-autopilot-sla`

Schedule:

- `45 22 * * *`

Owns:

- `autopilot-sla.json`
- `autopilot-sla.md`
- dashboard sync for SLA artifacts

### 4. `prod-idle-watchdog-observe`

Schedule:

- `7 * * * *`

Owns:

- `watchdog-monitor.json`
- `watchdog-monitor.md`

### 5. `prod-idle-watchdog-policy`

Schedule:

- `9 * * * *`

Owns:

- deterministic policy append for idle watchdog
- `REQUEST_MINI_CYCLE_HANDOFF` style summary decisions

## Internal OpenClaw jobs already retired from primary ownership

- `Daily ops state lint`
- `Deploy log capture and status audit`
- `Daily autopilot SLA tracker`

## Internal OpenClaw jobs still active

- `Autopilot sequential delivery cycle`
- `Autopilot idle watchdog`
- `Daily summary rotation`
- `Weekly code evolution KPI audit`
- `Weekly specialist productivity audit`

## Idle watchdog migration status

Implemented:

1. observe slice
2. policy slice
3. handoff request bridge
4. handoff consumer scaffold
5. execution bridge in `dry-run`

Current rule:

- internal `Autopilot idle watchdog` remains the only executor
- host-side lanes are deterministic and non-executing

## Why the current state is coherent

The migration has moved deterministic file-based and policy-based work out of the agent runtime first, while preserving risky autonomous execution inside OpenClaw until ownership transfer is explicitly gated.

## What remains for the next phase

1. cutover playbook for `Autopilot idle watchdog`
2. explicit execution ownership transfer gate
3. rollback-tested executor swap
