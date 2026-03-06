# Agent OS Green Long Soak Evidence

Date: 2026-03-05
Scope: extended Green validation in `openclaw-next` after the short soak, keeping production (`openclaw`) online and unchanged.

## Baseline

- Docker context:
  - `docker context ls && docker context show` -> `default`
- Containers online before soak:
  - `openclaw`
  - `openclaw-next`
- Production health before soak:
  - `Gateway Health OK (1314ms)`
  - `Telegram: ok (@StephenFryBot) (1313ms)`
- Candidate health before soak:
  - `Gateway Health OK (0ms)`
  - `Telegram: not configured`

## Commands executed

```bash
docker context ls && docker context show
docker ps
docker exec openclaw openclaw --profile prod gateway health
docker exec openclaw-next openclaw --profile prod gateway health
./control-plane/scripts/init_db.sh --db /tmp/agentos_green_long_soak.db
./control-plane/scripts/run_workflow.sh --db /tmp/agentos_green_long_soak.db --name daily_ops_state_lint --workspace-root ~/clawd-next
./control-plane/scripts/run_workflow.sh --db /tmp/agentos_green_long_soak.db --name daily_summary_rotation --workspace-root ~/clawd-next
sleep 20 && ./control-plane/scripts/run_workflow.sh --db /tmp/agentos_green_long_soak.db --name daily_ops_state_lint --workspace-root ~/clawd-next
sleep 20 && ./control-plane/scripts/run_workflow.sh --db /tmp/agentos_green_long_soak.db --name daily_summary_rotation --workspace-root ~/clawd-next
docker exec openclaw openclaw --profile prod gateway health
docker exec openclaw-next openclaw --profile prod gateway health
```

## Workflow results

### Cycle 1

#### `daily_ops_state_lint`

- Task ID: `2c09694e-5da0-416d-94c3-3d2e8279f715`
- Status: `succeeded`
- Stdout: `ops lint ok`
- Report artifact:
  - `control-plane/artifacts/reports/2c09694e-5da0-416d-94c3-3d2e8279f715-workflow-daily_ops_state_lint.json`

#### `daily_summary_rotation`

- Task ID: `421f0717-f3e5-4ed8-85d6-7d3b80e09c9e`
- Status: `succeeded`
- Stdout: `no-rotation-needed`
- Report artifact:
  - `control-plane/artifacts/reports/421f0717-f3e5-4ed8-85d6-7d3b80e09c9e-workflow-daily_summary_rotation.json`

### Cycle 2

#### `daily_ops_state_lint`

- Task ID: `c24c8864-f84e-44a7-a64e-ce02628d3773`
- Status: `succeeded`
- Stdout: `ops lint ok`
- Report artifact:
  - `control-plane/artifacts/reports/c24c8864-f84e-44a7-a64e-ce02628d3773-workflow-daily_ops_state_lint.json`

#### `daily_summary_rotation`

- Task ID: `c0c33940-938c-4979-9712-0e559c203209`
- Status: `succeeded`
- Stdout: `no-rotation-needed`
- Report artifact:
  - `control-plane/artifacts/reports/c0c33940-938c-4979-9712-0e559c203209-workflow-daily_summary_rotation.json`

## SQLite summary

Database: `/tmp/agentos_green_long_soak.db`

- Tasks:
  - `ops_watchdog` -> `succeeded` (`2`)
  - `daily_summary` -> `succeeded` (`2`)
- Events total: `16`
- Event types:
  - `task.created` (`4`)
  - `task.claimed` (`4`)
  - `task.progress` (`4`)
  - `task.completed` (`4`)
- Artifacts:
  - `workflow_report` (`4`)
  - `event_log` (`16`)
  - `evidence` (`16`)

## Post-soak health

- Production (`openclaw`):
  - `Gateway Health OK (1279ms)`
  - `Telegram: ok (@StephenFryBot) (1279ms)`
- Candidate (`openclaw-next`):
  - `Gateway Health OK (0ms)`
  - `Telegram: not configured`

## Operational conclusion

- The extended Green soak remained stable across repeated workflow executions and repeated health checks.
- No workflow failures, retries, or blocked states were observed in this soak window.
- No production regression was introduced.
- Green is ready for one more gated step: either another low-risk workflow integration or a longer timed observation window before any promotion decision.
