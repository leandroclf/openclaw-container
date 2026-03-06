# Operational Architecture State - 2026-03-06

## Objective

Capture the production operating model after the current Agent OS substitutions, with explicit ownership by lane.

## Production runtime

- Host: WSL Ubuntu 24.04
- Docker context: `default`
- Active container: `openclaw`
- Gateway:
  - bind: `loopback`
  - health: `OK`
  - Telegram: `ok (@StephenFryBot)`

## Active host-side lanes

### 1. Container ops lane

Owned by WSL cron:

- `healthcheck_notify.sh`
- `daily_maintenance.sh`
- `backup.sh`
- `update.sh`
- `model_router.py`
- `prune_logs.sh`

Purpose:

- keep container healthy
- rotate/update/backup safely
- keep routing policy refreshed

### 2. Agent OS collection lane

Owned by:

- `control-plane/scripts/prod_observe_cycle.sh`

Schedule:

- `17,47 * * * *`

Workflows:

- `daily_ops_state_lint`
- `product_progress_snapshot`
- `github_ci_status_collect`

Purpose:

- produce fresh operational artifacts without relying on interactive cron responses

Artifacts refreshed:

- `ops/multiagent/delivery/deploy-status.json/.md`
- `ops/multiagent/delivery/ci-regression-watchdog.json/.md`
- `ops/multiagent/delivery/product-code-progress.json/.md`
- `ops/multiagent/delivery/ops-lint-report.md`

Runtime evidence:

- DB: `~/openclaw/runtime/agentos/prod-observe.db`
- log: `~/openclaw/logs/agentos-prod-observe.log`

### 3. Agent OS policy lane

Owned by:

- `control-plane/scripts/prod_policy_audit_cycle.sh`

Schedule:

- `19,49 * * * *`

Purpose:

- consume collection artifacts only
- validate freshness
- apply `ALERT_OWNERSHIP_POLICY.md`
- append the decision to `daily-summary.md`

Inputs:

- `deploy-status.json`
- `ci-regression-watchdog.json`
- `product-code-progress.json`

Outputs:

- `ops/multiagent/delivery/daily-summary.md`
- host-side log `~/openclaw/logs/agentos-prod-policy-audit.log`

### 4. Agent OS SLA lane

Owned by:

- `control-plane/scripts/prod_autopilot_sla_cycle.sh`

Schedule:

- `45 22 * * *`

Purpose:

- deterministically refresh autopilot SLA artifacts
- sync dashboard data

Inputs:

- `ops/multiagent/delivery/autopilot-cycle-history.json`
- `ops/multiagent/delivery/daily-summary.md`

Outputs:

- `ops/multiagent/delivery/autopilot-sla.json`
- `ops/multiagent/delivery/autopilot-sla.md`
- `projects/site-lf-solucoes/dashboards/data/autopilot-sla.json`

Runtime evidence:

- log: `~/openclaw/logs/agentos-prod-autopilot-sla.log`

## Remaining internal OpenClaw cron responsibilities

Still owned by internal OpenClaw cron:

- `Autopilot sequential delivery cycle`
- `Autopilot idle watchdog`
- `Daily summary rotation`
- `Weekly code evolution KPI audit`
- `Weekly specialist productivity audit`

## Internal jobs already retired or removed from the critical path

- `Daily ops state lint`
- `Deploy log capture and status audit`
- `Daily autopilot SLA tracker`

## Architectural boundary

### Agent OS host-side now owns

- deterministic observation
- deterministic policy evaluation
- deterministic SLA generation

### Internal OpenClaw cron still owns

- autonomous delivery behavior
- watchdog behavior that can trigger subagent execution
- weekly governance flows

## Why this split is coherent

The current split follows one rule:

- deterministic file-based workflows move first
- stateful, agentic, or mutating workflows stay internal until their contracts are decomposed

This reduces runtime ambiguity and avoids keeping broken interactive cron paths active for tasks that can run deterministically on the host.
