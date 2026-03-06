# Next Migration Candidate - Idle Watchdog - 2026-03-06

## Candidate

Internal OpenClaw cron job:

- `Autopilot idle watchdog`

## Current behavior

The job currently asks an agent to:

1. run `python3 tools/watchdog_monitor.py`
2. interpret the resulting JSON
3. decide between:
   - `NO_ACTION`
   - `REPORT_BLOCKERS`
   - `TRIGGER_MINI_CYCLE`
4. write the outcome into `daily-summary.md`

## Why this is the next logical candidate

This job sits exactly at the boundary between:

- deterministic observation
- non-deterministic autonomous execution

That makes it the right next migration target after the deploy-audit and SLA substitutions.

## Technical reading of the current script

`tools/watchdog_monitor.py` already does deterministic work:

- reads `kanban.json`
- reads `semaphore-state.json`
- reads repo mappings
- checks repo activity via git
- computes:
  - `productive_advancement_detected`
  - `active_blockers_detected`
  - `eligible_auto_tasks`
  - `suggested_action`
  - `reason`

This means the script already cleanly produces a machine-readable decision artifact.

## What should be migrated first

Only the deterministic half should move first.

### Phase A - deterministic watchdog observation

Host-side runner should:

1. execute `python3 tools/watchdog_monitor.py`
2. persist the JSON result
3. write a host-side log
4. optionally append a deterministic summary block to `daily-summary.md`

Suggested outputs:

- `ops/multiagent/delivery/watchdog-monitor.json`
- `ops/multiagent/delivery/watchdog-monitor.md`
- `~/openclaw/logs/agentos-idle-watchdog.log`

### Phase B - policy wrapper for watchdog

After observation is stable, a wrapper should:

- read `watchdog-monitor.json`
- decide:
  - monitor only
  - report blockers
  - request mini-cycle handoff
- append the decision to `daily-summary.md`

### Phase C - handoff contract only

Only after A and B are stable should the system hand off a `TRIGGER_MINI_CYCLE` event into Agent OS or internal autopilot.

That handoff must not directly execute mutation in the first cut.

## What should not happen yet

Do not migrate in the first cut:

- direct triggering of the delivery cycle from host-side cron
- Telegram delivery behavior
- subagent spawning logic
- autonomous repo mutation

Reason:

Those are the highest-risk parts of the watchdog path and still need a clear contract boundary.

## Recommended target split

### Host-side Agent OS

Own:

- watchdog observation
- watchdog policy summary
- append-only evidence

### Internal OpenClaw

Temporarily keep owning:

- actual mini-cycle execution
- runtime subagent orchestration

## Acceptance criteria for the first migration cut

- `watchdog_monitor.py` runs host-side successfully
- JSON output is persisted
- deterministic summary is appended correctly
- no health regression
- no unwanted mini-cycle execution from host-side cron

## Decision

`Autopilot idle watchdog` is the strongest next migration candidate because it is the first workflow where Agent OS can take over observation and decision evidence, while still leaving the risky execution handoff inside OpenClaw until the next gate.
