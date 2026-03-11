# Agent OS Delivery Execution Prep

Date: 2026-03-10

## Goal

Advance the Agent OS migration from board-to-queue into executor-visible delivery handoff artifacts without mutating product repositories from the host-side lane.

## Scope

- Queue sync from `ops/multiagent/delivery/board.md`
- Supervisor promotion from `planning` to executor-ready `code_impl` / `research`
- Host-side export of a canonical delivery execution request

## New components

- `control-plane/scripts/prod_delivery_queue_cycle.sh`
- `control-plane/scripts/prod_delivery_handoff_cycle.sh`
- `control-plane/scripts/install_prod_delivery_cron.sh`
- `scripts/agentos.py export-delivery-handoff`

## Runtime paths

- DB: `~/openclaw/runtime/agentos/prod-delivery.db`
- Handoff artifact:
  - `~/openclaw/runtime/agentos/handoffs/delivery-execution-request.json`
  - `~/openclaw/runtime/agentos/handoffs/delivery-execution-request.md`

## Contract

- Host-side may:
  - sync board items
  - promote canonical tasks
  - export delivery handoff requests
- Host-side must not:
  - mutate product repositories directly
  - commit or push through this lane
  - bypass acceptance gates for code tasks

## Expected outcome

The runtime gains a canonical, inspectable handoff artifact for the next executor-ready delivery task, including repo readiness and the exact issue/repo/branch contract.
