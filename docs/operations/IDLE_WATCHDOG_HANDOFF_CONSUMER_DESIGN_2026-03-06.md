# Idle Watchdog Handoff Consumer Design - 2026-03-06

## Objective

Define the consumer contract for the idle watchdog handoff request without activating it yet.

## Inputs

- request artifact:
  - `~/openclaw/runtime/agentos/handoffs/watchdog-handoff-request.json`
- consumer state:
  - `~/openclaw/runtime/agentos/handoffs/watchdog-handoff-state.json`

## Precedence rule

While the internal `Autopilot idle watchdog` remains enabled:

- the host-side consumer must stay non-scheduled
- the internal watchdog remains the only executor
- the host-side consumer is allowed to evaluate readiness only

This avoids double-triggering mini-cycles.

## Readiness rules

The consumer should consider a request eligible only when:

1. request exists
2. `status = pending_internal_consumption`
3. request age <= 30 minutes
4. same `requestId` was not activated before

## Activation rule

Even with `--activate`, the current scaffold does **not** trigger the internal cron.

It only records:

- `lastActivatedRequestId`
- `status = activated`

This is intentional. The actual execution bridge must be a separate cut.

## Why this scaffold is useful

It proves the contract and idempotency path before any runtime integration.

It also creates the exact state file that a future execution bridge can rely on.

## Future activation gate

Only after all of the following:

1. internal watchdog is reduced or disabled
2. no duplicate trigger path remains
3. handoff request generation is repeatable
4. consumer readiness is repeatable

should a later bridge be allowed to call an executor.

## Current conclusion

The next safe step is not execution. It is proving that:

- the request remains stable
- readiness evaluation remains stable
- state transitions are idempotent
