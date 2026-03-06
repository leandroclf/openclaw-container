# GitHub CI Status Collect Validation - 2026-03-06

Scope: manual validation of the new Agent OS workflow `github_ci_status_collect`, without adding it to `prod-observe` yet.

## Registry entry

Added to:

- `control-plane/config/workflow_registry.json`

Workflow definition:

- name: `github_ci_status_collect`
- command:
  - `python3 tools/github_ci_status.py`
- evidence targets:
  - `ops/multiagent/delivery/deploy-status.json`
  - `ops/multiagent/delivery/deploy-status.md`
  - `ops/multiagent/delivery/ci-regression-watchdog.json`
  - `ops/multiagent/delivery/ci-regression-watchdog.md`

## Manual validation command

```bash
./control-plane/scripts/run_workflow.sh --db /tmp/agentos_github_ci_status_collect.db --name github_ci_status_collect --workspace-root ~/clawd
```

## Result

- Task ID: `8d8756ea-1e7a-40f1-9470-a83ea7fc41ee`
- Status: `succeeded`
- Stdout: `HEARTBEAT_OK`
- Stderr: empty
- Workflow report:
  - `control-plane/artifacts/reports/8d8756ea-1e7a-40f1-9470-a83ea7fc41ee-workflow-github_ci_status_collect.json`

## Artifacts refreshed in workspace

- `~/clawd/ops/multiagent/delivery/deploy-status.json`
- `~/clawd/ops/multiagent/delivery/deploy-status.md`
- `~/clawd/ops/multiagent/delivery/ci-regression-watchdog.json`
- `~/clawd/ops/multiagent/delivery/ci-regression-watchdog.md`

## Observed output sample

- `deploy-status.md` updated timestamp:
  - `2026-03-06T11:58:58.018277+00:00`
- `ci-regression-watchdog.md` status:
  - `green`

## Operational conclusion

- The workflow is valid and ready for optional scheduling in a future phase.
- It is not yet part of `prod-observe`.
- No runtime scheduling change was applied in this step.
