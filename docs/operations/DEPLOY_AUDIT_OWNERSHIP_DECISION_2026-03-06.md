# Deploy Audit Ownership Decision - 2026-03-06

Decision: keep `Deploy log capture and status audit` owned by the internal OpenClaw cron for now, and remove the redundant host-side daily `github_ci_status.py` cron line.

## Current overlap

### Host-side WSL cron

Current daily line:

```cron
20 7 * * * cd /home/leandro/clawd && GH_TOKEN="$(/home/leandro/.local/bin/gh auth token)" python3 tools/github_ci_status.py >> /home/leandro/clawd/logs/ci-regression-watchdog.log 2>&1
```

### Internal OpenClaw cron

Job:

- `Deploy log capture and status audit`

Payload executes:

- `python3 tools/github_ci_status.py`
- `python3 ops/multiagent/delivery/scripts/product_progress_snapshot.py`
- alert ownership policy and daily-summary registration

### Agent OS `prod-observe`

Currently executes:

- `daily_ops_state_lint`
- `product_progress_snapshot`

## Responsibility split

### Keep internal ownership

Keep `Deploy log capture and status audit` active because it still owns:

- CI/deploy status capture
- alert ownership policy application
- daily-summary evidence registration
- specialist escalation semantics

### Remove host-side duplicate

The host-side daily `github_ci_status.py` cron line is redundant because:

- the same script already runs from the internal cron
- the internal cron runs more frequently
- the internal cron wraps the output in richer operational behavior

Removing the host-side line does not remove the capability; it removes duplication only.

## Not changed in this decision

- internal `Deploy log capture and status audit` remains enabled
- `product_progress_snapshot` remains duplicated between internal cron and `prod-observe`

Reason:

- that duplication is partial and still tied to the internal audit job’s broader behavior
- it should be handled only after a dedicated refactor of the internal job payload

## Safe immediate action

- remove the host-side daily `github_ci_status.py` line from `crontab`

## Deferred action

- redesign internal `Deploy log capture and status audit` into:
  - CI/deploy audit + alert policy
  - separate ownership for `product_progress_snapshot`

Only after that should the internal job itself be simplified.
