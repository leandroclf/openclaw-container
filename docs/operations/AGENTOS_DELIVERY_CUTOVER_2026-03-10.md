# Agent OS Delivery Cutover

Date: 2026-03-10

## Goal

Replace the internal time-based ownership of `Autopilot sequential delivery cycle` with a host-side Agent OS delivery lane that:

1. syncs the canonical board into the SQLite queue
2. promotes executor-ready tasks
3. exports a delivery handoff artifact
4. validates consumer readiness
5. triggers the direct OpenClaw agent executor only through the handoff
6. reconciles result artifacts back into the queue

## Runtime ownership after cutover

Host-side lanes now own delivery orchestration:

- `prod-delivery-queue`
- `prod-delivery-handoff`
- `prod-delivery-consumer`
- `prod-delivery-execution`
- `prod-delivery-reconcile`

Internal OpenClaw no longer owns delivery scheduling or execution via cron.

- `Autopilot sequential delivery cycle` remains disabled and out of the main path.
- The host-side execution bridge now calls `openclaw agent --agent main` directly.

## Executor contract

The host-side execution bridge now:

- reads the canonical handoff request from `~/openclaw/runtime/agentos/handoffs`
- passes the embedded handoff JSON directly to `openclaw agent --agent main`
- requires the agent reply to include a canonical result JSON payload
- synthesizes a blocked canonical result when consumer/policy guards block execution
- archives processed handoff artifacts after reconcile so the next queued task can advance

## Active cron lanes

- queue: `13,43 * * * *`
- handoff: `15,45 * * * *`
- consumer: `17,47 * * * *`
- execution: `19,49 * * * *`
- reconcile: `21,51 * * * *`

## Current limitation

The delivery lane is now architecturally closed end-to-end. Current blockers are no longer orchestration gaps; they are execution blockers surfaced by the lane itself, for example:

- repository dirty state (`repo_dirty`)
- agent-side blocked result with explicit cause
- missing technical progress on a specific issue

These now reconcile back into the queue as canonical `blocked` task outcomes.

## Operational evidence

- Delivery queue DB: `~/openclaw/runtime/agentos/prod-delivery.db`
- Handoff artifacts: `~/openclaw/runtime/agentos/handoffs/delivery-execution-*`
- Host logs:
  - `~/openclaw/logs/agentos-prod-delivery-queue.log`
  - `~/openclaw/logs/agentos-prod-delivery-handoff.log`
  - `~/openclaw/logs/agentos-prod-delivery-consumer.log`
  - `~/openclaw/logs/agentos-prod-delivery-execution.log`
  - `~/openclaw/logs/agentos-prod-delivery-reconcile.log`
