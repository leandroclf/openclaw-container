# Idle Watchdog Cutover Playbook - 2026-03-06

## Objective

Define the future cutover procedure for transferring idle-watchdog execution ownership from the internal OpenClaw cron to the host-side Agent OS bridge.

## Preconditions

Do not run this cutover unless all are true:

1. `prod-idle-watchdog-observe` repeatability proven
2. `prod-idle-watchdog-policy` repeatability proven
3. handoff bridge generation proven
4. handoff consumer readiness proven
5. execution bridge `dry-run` proven
6. production health stable
7. rollback operator ready

## Readiness command

Use the host-side readiness assessor before any cutover decision:

```bash
python3 /home/leandro/openclaw-container/scripts/idle_watchdog_cutover_readiness.py \
  --bridge-dir /home/leandro/openclaw/runtime/agentos/handoffs
```

Expected status today:

- `NO_GO`
- failed check:
  - `internal_watchdog_primary`

The cutover must remain blocked until the readiness output becomes `GO`.

## Current blocker

The execution bridge is intentionally blocked because:

- `internalWatchdogPrimary = true`

No cutover should happen until this flag is changed by explicit operational decision.

## Proposed cutover sequence

### Phase 1 - Freeze

1. verify:
   - `docker context show`
   - `docker exec openclaw openclaw --profile prod gateway health`
2. verify current cron blocks:
   - `prod-idle-watchdog-observe`
   - `prod-idle-watchdog-policy`
3. ensure the latest handoff request is fresh

### Phase 2 - Enable execution bridge ownership

1. run execution bridge in controlled mode with:
   - `--activate`
   - `--internal-watchdog-primary false`
2. verify:
   - `watchdog-execution-intent.json`
   - `watchdog-execution-state.json`
   - `lastExecutedRequestId`

### Phase 3 - Disable internal watchdog

1. disable:
   - `Autopilot idle watchdog`
2. keep:
   - observe
   - policy
   - bridge
   - consumer
   - execution bridge

### Phase 4 - Observation window

Observe at least 2 scheduled cycles for:

- no duplicate execution
- healthy gateway
- correct handoff/request lifecycle
- expected `daily-summary.md` behavior

## Rollback

If any regression appears:

1. disable host-side execution bridge
2. re-enable internal `Autopilot idle watchdog`
3. keep observe/policy slices running
4. preserve all handoff/runtime artifacts for post-mortem

## Artifacts to inspect during cutover

- `~/openclaw/runtime/agentos/handoffs/watchdog-handoff-request.json`
- `~/openclaw/runtime/agentos/handoffs/watchdog-handoff-state.json`
- `~/openclaw/runtime/agentos/handoffs/watchdog-execution-intent.json`
- `~/openclaw/runtime/agentos/handoffs/watchdog-execution-state.json`
- `~/openclaw/logs/agentos-prod-idle-watchdog-observe.log`
- `~/openclaw/logs/agentos-prod-idle-watchdog-policy.log`

## Current decision

This playbook is documentation only. No cutover is executed in the current state.
