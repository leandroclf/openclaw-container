# Operations Guardrails

This folder contains the current production guardrails plus historical evidence
from the Agent OS migration.

## Files

- `OPERATIONS_DOC_INDEX_2026-03-10.md`
  - Canonical index of current vs historical operations documents.
- `PRODUCTION_CHANGE_POLICY.md`
  - Non-negotiable rules for zero-downtime change management.
- `BLUE_GREEN_WSL_DOCKER_DESKTOP.md`
  - Step-by-step parallel deployment runbook for WSL and optional Docker
    Desktop context usage.
- `TEST_STRATEGY.md`
  - Unit/integration/regression gates to prevent operational regressions.
- `PROMOTION_ROLLBACK_CHECKLIST.md`
  - Step-by-step promotion and rollback checklist for blue/green.
- `COMPOSE_BLUE_GREEN_USAGE.md`
  - Safe usage of compose templates for candidate and optional full migration.
- `VALIDATION_EVIDENCE_2026-02-28.md`
  - Executed command evidence for post-promotion validation and runtime fixes.

## Usage order

1. Read `OPERATIONS_DOC_INDEX_2026-03-10.md` to identify the current source of
   truth.
2. Read policy before any production change.
3. Run blue/green procedure only when a parallel candidate is actually needed.
4. Run test gates.
5. Promote only after functional and soak validation.
