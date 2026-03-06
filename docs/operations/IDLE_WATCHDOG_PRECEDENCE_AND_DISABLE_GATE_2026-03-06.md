# Idle Watchdog Precedence and Disable Gate - 2026-03-06

## Objective

Define the exact precedence rule between the internal OpenClaw watchdog executor and the host-side Agent OS handoff stack, plus the minimum gate required before disabling the internal cron.

## Current precedence rule

While the internal OpenClaw cron `Autopilot idle watchdog` remains enabled:

1. the internal watchdog is the **only** execution authority for mini-cycle triggering
2. host-side `observe` is **read-only**
3. host-side `policy` is **decision-only**
4. host-side `handoff bridge` is **artifact-only**
5. host-side `consumer` is **readiness-only**

This means:

- no host-side component may trigger mini-cycle execution
- no host-side component may call the internal cron directly
- `REQUEST_MINI_CYCLE_HANDOFF` is informational only until the executor ownership changes

## Current lane responsibilities

### Internal OpenClaw watchdog

Owns:

- evaluating and executing mini-cycle behavior
- runtime subagent orchestration
- existing watchdog-triggered execution semantics

### Host-side Agent OS watchdog stack

Owns:

- deterministic observation (`watchdog-monitor.json/.md`)
- deterministic policy append in `daily-summary.md`
- deterministic handoff artifact creation
- deterministic readiness evaluation

Does **not** own:

- execution
- Telegram delivery
- subagent spawning
- repo mutation

## Why this precedence is mandatory

Without a hard precedence rule, the system could trigger the same mini-cycle twice:

- once via the internal watchdog
- once via a host-side bridge consumer

That would create duplicate execution, conflicting evidence, and undefined ownership.

## Disable gate for the internal watchdog

The internal `Autopilot idle watchdog` may only be disabled after **all** conditions below are true:

1. **Observation repeatability proven**
   - at least 3 successful scheduled runs of `prod-idle-watchdog-observe`

2. **Policy repeatability proven**
   - at least 2 successful scheduled runs of `prod-idle-watchdog-policy`
   - deterministic `REQUEST_MINI_CYCLE_HANDOFF` or `MONITOR/REPORT_BLOCKERS` decisions

3. **Bridge repeatability proven**
   - handoff artifact generated repeatedly without duplication
   - `requestId` behavior confirmed idempotent

4. **Consumer repeatability proven**
   - readiness evaluation stable
   - no false `activated` state

5. **Execution contract implemented**
   - a dedicated execution bridge exists
   - it can consume one handoff request exactly once
   - it records `lastActivatedRequestId`
   - it prevents duplicate execution against the internal watchdog path

6. **Rollback defined**
   - host-side execution bridge can be disabled by removing one cron block
   - internal watchdog can be re-enabled immediately

7. **Parallel observation window completed**
   - at least one period where:
     - internal watchdog remains enabled
     - host-side stack remains active
     - no divergence or health regression is observed

## Disable sequence when the gate is met

Only after the gate is met:

1. freeze the host-side execution bridge config
2. verify production health
3. disable internal `Autopilot idle watchdog`
4. keep host-side execution bridge active
5. observe at least 2 cycles
6. if regression occurs:
   - disable host-side execution bridge
   - re-enable internal watchdog

## Current conclusion

The gate is **not met yet**.

What is already true:

- observation repeatability
- policy repeatability
- bridge scaffold exists
- consumer scaffold exists

What is still missing:

- execution bridge
- duplicate-execution prevention at executor level
- formal rollback test for watchdog ownership transfer
