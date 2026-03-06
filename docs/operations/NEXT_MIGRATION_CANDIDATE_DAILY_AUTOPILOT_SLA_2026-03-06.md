# Next Migration Candidate - Daily Autopilot SLA Tracker - 2026-03-06

## Candidate

Internal OpenClaw cron job:

- `Daily autopilot SLA tracker`

## Why this is the next logical target

This job is a better next migration candidate than any delivery or Telegram-facing workflow because it is:

- deterministic
- file-based
- low-risk
- already partially failing in the current internal runtime

Observed current state:

- internal cron job remains enabled
- latest known state includes `lastRunStatus = error`
- its inputs are local artifacts, not product repo mutations

## Current responsibility

The job updates:

- `ops/multiagent/delivery/autopilot-sla.json`
- `ops/multiagent/delivery/autopilot-sla.md`

using:

- `ops/multiagent/delivery/autopilot-cycle-history.json`
- `ops/multiagent/delivery/daily-summary.md`

## Why it fits Agent OS

It matches the existing migration pattern already proven in production:

1. collection / observation lane remains separate
2. a deterministic host-side wrapper consumes artifacts
3. output is written to local markdown/json
4. production health does not depend on an interactive agent response

## What should *not* be migrated next

Not recommended as the immediate next step:

- `Autopilot sequential delivery cycle`
- `Autopilot idle watchdog`
- any commit/push/remediation flow
- Telegram delivery flows

Reason:

These have higher behavioral risk and still depend on ownership, escalation, and product-side execution semantics that are not yet cleanly separated.

## Proposed migration path

### Phase 1

Create a host-side deterministic runner for the SLA tracker.

Expected script:

- `control-plane/scripts/prod_autopilot_sla_cycle.sh`

Expected behavior:

- run the SLA update logic against the workspace
- validate output files exist and are fresh
- write host-side log
- keep production gateway healthy before/after

### Phase 2

Schedule it in host cron with its own lock/log.

Expected block:

- `OpenClaw Agent OS Prod autopilot SLA`

### Phase 3

Observe at least two scheduled runs.

### Phase 4

Disable the internal OpenClaw cron job only after equivalence is proven.

## Acceptance criteria

- output files updated successfully
- no production health regression
- no Telegram regression
- repeated scheduled runs succeed
- internal job can be disabled without loss of reporting

## Decision

`Daily autopilot SLA tracker` is the strongest next migration candidate because it increases coherence and reduces risk before any attempt to move delivery/autopilot execution itself.
