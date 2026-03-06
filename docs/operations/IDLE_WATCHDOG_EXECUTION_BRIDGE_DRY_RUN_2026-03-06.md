# Idle Watchdog Execution Bridge Dry Run - 2026-03-06

## Objective

Prepare the execution-bridge contract for the idle watchdog while keeping activation blocked until ownership transfer is approved.

## Inputs

- `~/openclaw/runtime/agentos/handoffs/watchdog-handoff-request.json`
- `~/openclaw/runtime/agentos/handoffs/watchdog-handoff-state.json`

## Outputs

- `~/openclaw/runtime/agentos/handoffs/watchdog-execution-intent.json`
- `~/openclaw/runtime/agentos/handoffs/watchdog-execution-intent.md`
- `~/openclaw/runtime/agentos/handoffs/watchdog-execution-state.json`

## Dry-run behavior

The bridge:

1. validates request freshness
2. validates consumer readiness
3. validates duplicate protection
4. checks whether the internal watchdog is still primary

With the current production state:

- `internalWatchdogPrimary=true`

Therefore:

- dry-run may become `ready`
- activation must remain `blocked`

## Safety rule

No execution bridge activation is allowed while:

- the internal `Autopilot idle watchdog` remains enabled as primary executor

## Next activation gate

Only after the precedence document gate is met should the bridge be invoked with `--activate --internal-watchdog-primary false`.
