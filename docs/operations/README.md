# Operations Guardrails

This folder contains mandatory operational guardrails to keep OpenClaw online
while evolving infrastructure.

## Files

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

1. Read policy before any production change.
2. Run blue/green procedure for candidate validation.
3. Run test gates.
4. Promote only after functional and soak validation.
