# Agent OS Green Soak Evidence

Date: 2026-03-05
Scope: short soak window in Green only (`openclaw-next`) after Wave 3, with production (`openclaw`) kept online and unchanged.

## Baseline

- Docker context:
  - `docker context ls && docker context show` -> `default`
- Containers online before soak:
  - `openclaw`
  - `openclaw-next`
- Production health before soak:
  - `Gateway Health OK`
  - `Telegram: ok (@StephenFryBot)`
- Candidate health before soak:
  - `Gateway Health OK`
  - `Telegram: not configured`

## Commands executed

```bash
docker context ls && docker context show
docker ps
docker exec openclaw openclaw --profile prod gateway health
docker exec openclaw-next openclaw --profile prod gateway health
./control-plane/scripts/init_db.sh --db /tmp/agentos_green_soak.db
./control-plane/scripts/run_workflow.sh --db /tmp/agentos_green_soak.db --name daily_ops_state_lint --workspace-root ~/clawd-next
./control-plane/scripts/run_workflow.sh --db /tmp/agentos_green_soak.db --name daily_summary_rotation --workspace-root ~/clawd-next
sleep 10 && docker exec openclaw openclaw --profile prod gateway health
sleep 10 && docker exec openclaw-next openclaw --profile prod gateway health
```

## Workflow results

### `daily_ops_state_lint`

- Task ID: `808e09a7-3691-419d-9d2c-1b12b6920222`
- Status: `succeeded`
- Stdout: `ops lint ok`
- Report artifact:
  - `control-plane/artifacts/reports/808e09a7-3691-419d-9d2c-1b12b6920222-workflow-daily_ops_state_lint.json`

### `daily_summary_rotation`

- Task ID: `b0acd60a-564a-42cb-b8ee-dca250b303f5`
- Status: `succeeded`
- Stdout: `no-rotation-needed`
- Report artifact:
  - `control-plane/artifacts/reports/b0acd60a-564a-42cb-b8ee-dca250b303f5-workflow-daily_summary_rotation.json`

## SQLite summary

Database: `/tmp/agentos_green_soak.db`

- Tasks:
  - `ops_watchdog` -> `succeeded` (`1`)
  - `daily_summary` -> `succeeded` (`1`)
- Events total: `8`
- Event types:
  - `task.created` (`2`)
  - `task.claimed` (`2`)
  - `task.progress` (`2`)
  - `task.completed` (`2`)

## Post-soak health

- Production (`openclaw`):
  - `Gateway Health OK (1280ms)`
  - `Telegram: ok (@StephenFryBot) (1280ms)`
- Candidate (`openclaw-next`):
  - `Gateway Health OK (0ms)`
  - `Telegram: not configured`

## Operational conclusion

- The short Green soak stayed stable across baseline, workflow execution, and post-run health checks.
- No production regression was introduced.
- The candidate remains suitable for the next gated step: extending Green validation to another low-risk workflow or starting a longer soak window before any promotion decision.
