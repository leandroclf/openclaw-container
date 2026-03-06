# Agent OS Green Wave 3 Evidence

Date: 2026-03-05
Scope: low-risk workflow integration in Green only (`openclaw-next`), keeping production unchanged.

## Selected workflows

- `daily_ops_state_lint`
- Source script: `~/clawd-next/ops/multiagent/delivery/scripts/ops_state_lint.py`
- `daily_summary_rotation`
- Source script: `~/clawd-next/ops/multiagent/delivery/scripts/daily_summary_rotate.py`
- Agent OS registry entry: `control-plane/config/workflow_registry.json`

## Commands executed

```bash
./control-plane/scripts/init_db.sh --db /tmp/agentos_green_wave3.db
./control-plane/scripts/run_workflow.sh --db /tmp/agentos_green_wave3.db --name daily_ops_state_lint --workspace-root ~/clawd-next
./control-plane/scripts/init_db.sh --db /tmp/agentos_green_wave3c.db
./control-plane/scripts/run_workflow.sh --db /tmp/agentos_green_wave3c.db --name daily_summary_rotation --workspace-root ~/clawd-next
docker exec openclaw-next openclaw --profile prod gateway health
```

## Results

### Workflow execution

#### `daily_ops_state_lint`

- Task ID: `c271e29a-ec59-4563-8d35-00dba5e79306`
- Task status: `succeeded`
- Workflow stdout: `ops lint ok`
- Workflow stderr: empty
- Agent OS report artifact:
  - `control-plane/artifacts/reports/c271e29a-ec59-4563-8d35-00dba5e79306-workflow-daily_ops_state_lint.json`

#### `daily_summary_rotation`

- Task ID: `4db8d10a-16a6-49bf-9538-7128ac1bdb18`
- Task status: `succeeded`
- Workflow stdout: `no-rotation-needed`
- Workflow stderr: empty
- Agent OS report artifact:
  - `control-plane/artifacts/reports/4db8d10a-16a6-49bf-9538-7128ac1bdb18-workflow-daily_summary_rotation.json`
- Compatibility note:
  - the Agent OS runner rewrote the hardcoded `/home/node/clawd` path in the workflow script to the candidate workspace root before execution.

### Evidence generated in the candidate workspace

- `~/clawd-next/ops/multiagent/delivery/ops-lint-report.md`
- `~/clawd-next/ops/multiagent/delivery/daily-summary.md`

### Event sequence persisted in SQLite

For both workflows:
- `task.created`
- `task.claimed`
- `task.progress`
- `task.completed`

### Candidate runtime health after Wave 3

- `Gateway Health OK`
- `Telegram: not configured`

## Operational conclusion

- Wave 3 succeeded for two low-risk workflows in Green.
- Production was not modified.
- The next logical step is to start a controlled soak window for the current Green state before broader integration.
