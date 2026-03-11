# Agent OS Delivery Queue Prep - 2026-03-10

## Goal

Advance the migration from an operations-oriented control plane to a real
delivery-oriented Agent OS by connecting the workspace kanban to canonical Agent
OS tasks.

## What was implemented

- `scripts/agentos.py` now parses the canonical delivery board:
  - `ops/multiagent/delivery/board.md`
- New command:
  - `python3 scripts/agentos.py sync-board --db <db> --workspace-root /home/leandro/clawd`
- AUTO issues from `AUTHORIZED` and `IN PROGRESS` become canonical queue tasks.
- Product issues with repository metadata are normalized into:
  - root `planning` tasks
  - derived `code_impl` executor tasks after `supervisor-cycle --unsafe-mode`

## Why this matters

Before this change, the Agent OS control plane was mostly strong for:

- runtime operations
- collection
- policy
- SLA
- watchdog

But it was weak on actual delivery orchestration.

This change creates the missing bridge:

- kanban/workspace intent
- canonical task queue
- planner/executor handoff

## Current behavior

### Root task

- kind: `planning`
- source: `board`
- correlation: `board:<ISSUE-ID>`
- issue metadata preserved from `board.md`

### Derived executor task

- kind: `code_impl` when repo exists
- kind: `research` when repo does not exist
- acceptance for code tasks:
  - `test`
  - `commit`
  - `pr_or_pr_update`
  - `ciMustPass=true`

## Validation run

Validated against the live workspace board with a temp DB:

- `ISSUE-001` -> queued `planning` task -> derived `code_impl`
- `ISSUE-002` -> queued `planning` task -> derived `code_impl`
- `ISSUE-003` -> queued `planning` task -> derived `code_impl`

Non-AUTO items were skipped.
Existing active issue tasks were skipped idempotently.

## Boundary

This does **not** yet execute code automatically in the product repositories.

What it does now:

- canonicalizes delivery issues into queue state
- derives executor-ready tasks
- creates observable handoff events and blockers

What still remains:

- execution worker for `code_impl`
- evidence writer for commit/PR/test result ingestion
- automatic board state writeback
