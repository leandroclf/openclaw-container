# Idle Watchdog Handoff Bridge Design - 2026-03-06

## Purpose

Define the bridge between the host-side deterministic idle watchdog policy lane and the still-internal mini-cycle executor.

## Problem

The host-side lane now produces a stable deterministic decision:

- `REQUEST_MINI_CYCLE_HANDOFF`

But there is no safe contract yet for passing that request into the internal executor without risking duplicate execution.

## Design choice

Use an explicit, idempotent handoff artifact outside the workspace:

- host path: `~/openclaw/runtime/agentos/handoffs/watchdog-handoff-request.json`
- companion markdown: `~/openclaw/runtime/agentos/handoffs/watchdog-handoff-request.md`

Reason:

- avoids adding more churn to the already-dirty workspace repo
- keeps handoff state in runtime territory, not source control territory
- creates a clean consumption point for a later internal bridge

## Contract

The bridge artifact is created only when:

- `watchdog-monitor.json` is fresh
- `active_blockers_detected=false`
- `suggested_action=TRIGGER_MINI_CYCLE`

The artifact includes:

- `requestId`
- `createdAt`
- `status=pending_internal_consumption`
- source metadata
- tracked candidate tasks

## Idempotency

`requestId` is derived from:

- observed timestamp
- suggested action
- reason
- tracked task ids
- eligible task count

If the same request is already pending, the bridge performs `NOOP`.

## Important safety rule

This bridge does **not**:

- call the internal cron
- send Telegram
- execute mini-cycles
- mutate product repos

It only publishes a handoff request.

## Next activation gate

Future activation should require:

1. repeated successful host-side observe/policy runs
2. repeated stable bridge artifact generation
3. a clearly defined internal consumer contract
4. duplicate-execution prevention between:
   - internal `Autopilot idle watchdog`
   - host-side bridge consumer
