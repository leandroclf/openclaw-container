# Agent OS Full Cutover - 2026-03-10

## Scope

Complete the production migration from the remaining internal idle-watchdog
executor to the host-side Agent OS chain.

## Runtime Upgrade

- OpenClaw image/runtime upgraded to `2026.3.8`
- release source:
  - `https://github.com/openclaw/openclaw/releases/tag/v2026.3.8`

## New Release Features Adopted

- Brave web search grounding mode enabled:
  - `tools.web.search.brave.mode = llm-context`
- Cron announce delivery and config snapshot fixes inherited from `2026.3.8`
- native backup CLI available in production runtime:
  - `openclaw backup create`
  - `openclaw backup verify`
- ACP provenance support available in runtime:
  - `openclaw acp --provenance meta+receipt`

## Idle Watchdog Ownership

### Internal executor

- `Autopilot idle watchdog` -> disabled

### Host-side executor chain

- `prod-idle-watchdog-observe`
- `prod-idle-watchdog-policy`
- `prod-idle-watchdog-handoff`
- `prod-idle-watchdog-consumer`
- `prod-idle-watchdog-execution`

## Activation Result

- readiness gate returned `GO`
- execution bridge activated successfully
- internal delivery cycle triggered through:
  - `Autopilot sequential delivery cycle`

## Production Health

- gateway health: `OK`
- Telegram channel: `ok`

## Current Ownership Model

- collection/policy/watchdog execution now run through host-side Agent OS lanes
- the internal sequential delivery cycle remains the delivery executor that the
  host-side execution bridge triggers intentionally

## Remaining Internal OpenClaw Cron Jobs

- `Autopilot sequential delivery cycle`
- `Daily summary rotation`
- `Weekly code evolution KPI audit`
- `Weekly specialist productivity audit`

## Rollback Boundary

If the new host-side watchdog chain regresses:

1. remove host-side idle-watchdog handoff/consumer/execution cron blocks
2. re-enable internal `Autopilot idle watchdog`
3. keep production container and data volumes intact
