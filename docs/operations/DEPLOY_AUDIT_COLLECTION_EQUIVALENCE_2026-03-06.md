# Deploy Audit Collection Equivalence - 2026-03-06

Purpose: compare the collection portion of the internal `Deploy log capture and status audit` job with the new Agent OS workflow `github_ci_status_collect`.

## Evidence collected

### Internal OpenClaw cron

Job:

- `Deploy log capture and status audit`

Observed state from `cron list`:

- `lastRunAtMs` -> `2026-03-06T09:12:02.047-03:00`
- `lastStatus` -> `ok`
- `lastDurationMs` -> `180232`

This confirms the internal job executed successfully at `09:12`.

### Agent OS production observe

Scheduled run observed:

- `2026-03-06T09:17:05-03:00` to `2026-03-06T09:17:19-03:00`

Task:

- `github_ci_status_collect` -> `1d912128-6f2d-4d02-acd3-5028dafed7a1`

Workflow report:

- `control-plane/artifacts/reports/1d912128-6f2d-4d02-acd3-5028dafed7a1-workflow-github_ci_status_collect.json`

Observed report fields:

- `returnCode = 0`
- `stdout = HEARTBEAT_OK`
- `workspaceRoot = /home/leandro/clawd`

## Shared artifacts

The Agent OS workflow refreshes the same collection artifacts used by the internal job:

- `~/clawd/ops/multiagent/delivery/deploy-status.json`
- `~/clawd/ops/multiagent/delivery/deploy-status.md`
- `~/clawd/ops/multiagent/delivery/ci-regression-watchdog.json`
- `~/clawd/ops/multiagent/delivery/ci-regression-watchdog.md`

Observed mtimes after the Agent OS scheduled run:

- `deploy-status.json` -> `2026-03-06 09:17:17 -03:00`
- `ci-regression-watchdog.json` -> `2026-03-06 09:17:17 -03:00`

This shows:

1. the internal job completed at `09:12`
2. the Agent OS collect workflow completed at `09:17`
3. both target the same collection artifacts

## What this proves

- The `collection` portion of the internal deploy audit job is now functionally duplicated by Agent OS.
- The Agent OS path can produce the collection artifacts successfully in production.
- No health regression occurred during the Agent OS path.

## What this does not prove yet

- It does not yet replace:
  - alert ownership policy application
  - `daily-summary.md` incident registration
  - delivery/escalation behavior

Those behaviors still belong to the internal OpenClaw job.

## Safe next cut

The next safe cut is not to disable the internal job wholesale.

The next safe cut is to refactor the internal job so that:

- `collection` is no longer its responsibility
- `policy + summary + escalation` remain its responsibility

Only after that split should the collection part be removed from the internal path.
