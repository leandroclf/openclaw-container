# Operations Document Index - 2026-03-10

Purpose: provide a single index for the current production operating model after
the full Agent OS cutover and identify which older migration documents are now
historical evidence only.

## Canonical documents (current)

Read these first when operating or changing production:

1. `PRODUCTION_CHANGE_POLICY.md`
   - Non-negotiable production guardrails.
2. `PROMOTION_ROLLBACK_CHECKLIST.md`
   - Promotion and rollback gate for production-impacting changes.
3. `README.md`
   - Current helper scripts and day-2 operations entry point.
4. `AGENTOS_FULL_CUTOVER_2026-03-10.md`
   - Current production ownership model after the full host-side cutover.
5. `AGENTOS_PARTIAL_MIGRATION_FINAL_CHECKLIST_2026-03-06.md`
   - Final verification checklist that still applies to the hardened runtime.
6. `IDLE_WATCHDOG_CUTOVER_PLAYBOOK_2026-03-06.md`
   - Formal cutover/rollback procedure for the watchdog chain.
7. `IDLE_WATCHDOG_MANUAL_ACTIVATION_GATE_2026-03-06.md`
   - Guarded manual activation path for future watchdog ownership changes.

## Current reference architecture (active, but supporting)

These describe the live operating model and are still useful for design or
troubleshooting, but they are not the first documents to read for routine ops.

- `OPERATIONAL_ARCHITECTURE_STATE_2026-03-06.md`
- `AGENTOS_MIGRATION_STATE_SUMMARY_2026-03-06.md`
- `BLUE_GREEN_WSL_DOCKER_DESKTOP.md`
- `COMPOSE_BLUE_GREEN_USAGE.md`
- `TEST_STRATEGY.md`
- `TOKEN_COST_REDUCTION_STRATEGY.md`

## Historical evidence (keep, do not use as primary source)

These documents remain valuable as execution evidence, but they describe
intermediate states that are no longer the target production topology.

### Green validation and soak evidence

- `AGENTOS_GREEN_ROLLOUT_PLAN.md`
- `AGENTOS_GREEN_WAVE3_EVIDENCE.md`
- `AGENTOS_GREEN_WAVE4_PRODUCT_PROGRESS_EVIDENCE.md`
- `AGENTOS_GREEN_SOAK_EVIDENCE.md`
- `AGENTOS_GREEN_LONG_SOAK_EVIDENCE.md`
- `AGENTOS_GREEN_SCHEDULED_OBSERVATION.md`
- `AGENTOS_GREEN_SCHEDULED_OBSERVATION_EVIDENCE.md`
- `AGENTOS_GREEN_SCHEDULED_OBSERVATION_RUN_2026-03-06.md`
- `AGENTOS_GREEN_SCHEDULED_OBSERVATION_REPEATABILITY_2026-03-06.md`

### Partial migration state and promotion prep

- `AGENTOS_PARTIAL_PROMOTION_GATE.md`
- `AGENTOS_PROD_OBSERVE_PREP.md`
- `AGENTOS_PROD_OBSERVE_ACTIVATION_2026-03-06.md`
- `AGENTOS_PROD_OBSERVE_FIRST_SCHEDULED_RUN_2026-03-06.md`
- `AGENTOS_PROD_OBSERVE_REPEATABILITY_2026-03-06.md`
- `RUNTIME_STATE_POST_PARTIAL_MIGRATION_2026-03-06.md`

### Deploy-audit migration evidence

- `DEPLOY_AUDIT_MIGRATION_DESIGN_2026-03-06.md`
- `DEPLOY_AUDIT_COLLECTION_EQUIVALENCE_2026-03-06.md`
- `DEPLOY_AUDIT_POLICY_WRAPPER_REFACTOR_2026-03-06.md`
- `DEPLOY_AUDIT_OWNERSHIP_DECISION_2026-03-06.md`
- `GITHUB_CI_STATUS_COLLECT_VALIDATION_2026-03-06.md`
- `GITHUB_CI_STATUS_COLLECT_PROD_OBSERVE_ACTIVATION_2026-03-06.md`
- `GITHUB_CI_STATUS_COLLECT_PROD_OBSERVE_FIRST_SCHEDULED_RUN_2026-03-06.md`
- `AGENTOS_PROD_POLICY_AUDIT_FIRST_SCHEDULED_RUN_2026-03-06.md`
- `AGENTOS_PROD_POLICY_AUDIT_REPEATABILITY_2026-03-06.md`

### Autopilot SLA migration evidence

- `NEXT_MIGRATION_CANDIDATE_DAILY_AUTOPILOT_SLA_2026-03-06.md`
- `AGENTOS_PROD_AUTOPILOT_SLA_PREP_2026-03-06.md`
- `AGENTOS_PROD_AUTOPILOT_SLA_INTERNAL_DISABLE_DECISION_2026-03-06.md`

### Idle watchdog migration evidence

- `NEXT_MIGRATION_CANDIDATE_IDLE_WATCHDOG_2026-03-06.md`
- `NEXT_STEP_IDLE_WATCHDOG_EXECUTION_BRIDGE_2026-03-06.md`
- `AGENTOS_PROD_IDLE_WATCHDOG_OBSERVE_PREP_2026-03-06.md`
- `AGENTOS_PROD_IDLE_WATCHDOG_POLICY_PREP_2026-03-06.md`
- `AGENTOS_PROD_IDLE_WATCHDOG_FIRST_SCHEDULED_RUN_2026-03-06.md`
- `AGENTOS_PROD_IDLE_WATCHDOG_REPEATABILITY_2026-03-06.md`
- `IDLE_WATCHDOG_HANDOFF_BRIDGE_DESIGN_2026-03-06.md`
- `IDLE_WATCHDOG_HANDOFF_CONSUMER_DESIGN_2026-03-06.md`
- `IDLE_WATCHDOG_PRECEDENCE_AND_DISABLE_GATE_2026-03-06.md`
- `IDLE_WATCHDOG_EXECUTION_BRIDGE_PREP_2026-03-06.md`
- `IDLE_WATCHDOG_EXECUTION_BRIDGE_DRY_RUN_2026-03-06.md`
- `IDLE_WATCHDOG_CUTOVER_READINESS_2026-03-06.md`

### Cleanup and ownership decisions

- `CRON_CLEANUP_ANALYSIS_2026-03-06.md`
- `DAILY_SUMMARY_ROTATION_OWNERSHIP_DECISION_2026-03-06.md`
- `VALIDATION_EVIDENCE_2026-02-28.md`

## Superseded assumptions

The following assumptions are no longer current and should not guide new
changes:

- "Agent OS is observe-only in production."
- "Autopilot idle watchdog is still the primary executor."
- "Green validation assets are still part of live runtime."
- "Deploy log capture and status audit is still owned by an internal cron job."

## Recommended reading order for new operators

1. `README.md`
2. `PRODUCTION_CHANGE_POLICY.md`
3. `PROMOTION_ROLLBACK_CHECKLIST.md`
4. `AGENTOS_FULL_CUTOVER_2026-03-10.md`
5. `IDLE_WATCHDOG_CUTOVER_PLAYBOOK_2026-03-06.md`
6. `OPERATIONS_DOC_INDEX_2026-03-10.md`
