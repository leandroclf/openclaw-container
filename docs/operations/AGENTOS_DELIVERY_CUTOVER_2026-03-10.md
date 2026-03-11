# Agent OS Delivery Cutover

Date: 2026-03-10

## Goal

Replace the internal time-based ownership of `Autopilot sequential delivery cycle` with a host-side Agent OS delivery lane that:

1. syncs the canonical board into the SQLite queue
2. promotes executor-ready tasks
3. exports a delivery handoff artifact
4. validates consumer readiness
5. triggers the internal executor backend only through the handoff
6. reconciles result artifacts back into the queue

## Runtime ownership after cutover

Host-side lanes now own delivery orchestration:

- `prod-delivery-queue`
- `prod-delivery-handoff`
- `prod-delivery-consumer`
- `prod-delivery-execution`
- `prod-delivery-reconcile`

Internal OpenClaw keeps only the executor backend:

- `Autopilot sequential delivery cycle`

The internal delivery cron schedule is disabled. The job is now triggered manually by id from the host-side execution bridge.

## Internal executor contract

The internal executor payload was rewritten to:

- read `/home/node/.openclaw/agentos/handoffs/delivery-execution-request.json`
- work only on that handoff
- use `repo_access_preflight.py`
- avoid SSH and use `./bin/git-safe`
- write `/home/node/.openclaw/agentos/handoffs/delivery-execution-result.json`

## Active cron lanes

- queue: `13,43 * * * *`
- handoff: `15,45 * * * *`
- consumer: `17,47 * * * *`
- execution: `19,49 * * * *`
- reconcile: `21,51 * * * *`

## Current limitation

The host-side chain is fully active, but the final proof of end-to-end completion still depends on the internal executor writing `delivery-execution-result.json` as instructed. Until that artifact is observed, the reconcile lane will remain in `no_result`.

## Operational evidence

- Delivery queue DB: `~/openclaw/runtime/agentos/prod-delivery.db`
- Handoff artifacts: `~/openclaw/runtime/agentos/handoffs/delivery-execution-*`
- Host logs:
  - `~/openclaw/logs/agentos-prod-delivery-queue.log`
  - `~/openclaw/logs/agentos-prod-delivery-handoff.log`
  - `~/openclaw/logs/agentos-prod-delivery-consumer.log`
  - `~/openclaw/logs/agentos-prod-delivery-execution.log`
  - `~/openclaw/logs/agentos-prod-delivery-reconcile.log`
