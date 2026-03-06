# Idle Watchdog Cutover Readiness - 2026-03-06

## Purpose

Provide a deterministic `GO/NO_GO` check before transferring executor ownership
from the internal OpenClaw idle watchdog to the host-side execution bridge.

## Command

```bash
python3 /home/leandro/openclaw-container/scripts/idle_watchdog_cutover_readiness.py \
  --bridge-dir /home/leandro/openclaw/runtime/agentos/handoffs
```

## Outputs

- `~/openclaw/runtime/agentos/handoffs/watchdog-cutover-readiness.json`
- `~/openclaw/runtime/agentos/handoffs/watchdog-cutover-readiness.md`

## Current Expected Result

- `status: NO_GO`
- reason:
  - internal `Autopilot idle watchdog` remains enabled and is still the primary executor

## Minimum GO Criteria

1. handoff request exists and is fresh
2. consumer state is `ready`
3. execution bridge has prepared state for the same `requestId`
4. internal `Autopilot idle watchdog` is no longer enabled
5. `gateway health` is `OK`

## Rollback Relevance

If a future cutover happens, this readiness report must be captured both before
and after the ownership change to prove whether rollback is required.
