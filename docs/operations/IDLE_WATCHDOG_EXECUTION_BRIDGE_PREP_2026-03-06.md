# Idle Watchdog Execution Bridge Prep - 2026-03-06

## Goal

Prepare the production execution-bridge lane without transferring executor
ownership away from the internal `Autopilot idle watchdog`.

## Assets Added

- `control-plane/scripts/prod_idle_watchdog_execution_bridge_cycle.sh`
- `control-plane/scripts/install_prod_idle_watchdog_execution_bridge_cron.sh`
- `cron/cron.example` optional execution-bridge block

## Execution Contract

- Reads handoff artifacts from `~/openclaw/runtime/agentos/handoffs`
- Runs `scripts/idle_watchdog_execution_bridge.py`
- Forces `--internal-watchdog-primary true`
- Validates `gateway health` before and after execution
- Produces log target:
  - `~/openclaw/logs/agentos-prod-idle-watchdog-execution.log`

## Current Ownership

- Internal OpenClaw watchdog remains the sole executor.
- Host-side execution bridge remains a prepared lane only.
- No cron installation was performed in this step.

## Expected Dry-Run Result

- Output: `[EXECUTION_BLOCKED] requestId=<id>`
- Guard reason:
  - `internalWatchdogPrimary: true`

## Activation Gate

Do not install the cron block until all items below are true:

1. Internal watchdog executor ownership has a cutover decision approved.
2. Duplicate protection is validated against the internal watchdog cadence.
3. Immediate rollback path is documented and rehearsed.
