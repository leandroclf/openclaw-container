# Deploy Audit Migration Design - 2026-03-06

Purpose: define the next migration phase for `Deploy log capture and status audit` without changing the runtime in this step.

## Current behavior

The internal OpenClaw cron job `Deploy log capture and status audit` currently does all of the following in one job:

1. runs `python3 tools/github_ci_status.py`
2. runs `python3 ops/multiagent/delivery/scripts/product_progress_snapshot.py`
3. applies `ALERT_OWNERSHIP_POLICY.md`
4. records evidence in `ops/multiagent/delivery/daily-summary.md`
5. announces a summary through OpenClaw delivery

## Current ownership problem

This job mixes three different concerns:

### Concern A — raw CI/deploy collection

- GitHub Actions polling
- workflow run inspection
- regression watchdog generation

### Concern B — product progress snapshot

- local repo fetch/status
- PR count lookup
- factual snapshot generation

### Concern C — orchestration/policy

- alert severity decision
- owner assignment
- daily-summary reporting
- notification behavior

That mixture is the reason the job cannot be cleanly replaced in one move.

## Current overlap with production Agent OS

`prod-observe` already covers:

- `product_progress_snapshot`

It does **not** cover yet:

- `github_ci_status.py`
- alert ownership policy application
- daily-summary escalation semantics
- delivery behavior

## Migration target

The target is **not** to delete the internal job immediately.

The target is to split it into two explicit layers:

### Layer 1 — Agent OS observation workflow

Host-side or Agent OS-managed workflow(s) that produce structured evidence:

- `github_ci_status_collect`
- `product_progress_snapshot`

Outputs:

- JSON/MD artifacts
- Agent OS task/event history
- workflow reports

### Layer 2 — policy/orchestration wrapper

A thin decision layer that:

- reads the artifacts
- applies `ALERT_OWNERSHIP_POLICY.md`
- writes `daily-summary.md`
- decides whether to announce/escalate

This second layer may remain internal longer if needed.

## Recommended phased migration

### Phase 1 — current state

Keep current internal job unchanged.

Reason:

- production is stable
- `prod-observe` is still observe-only

### Phase 2 — add a dedicated Agent OS workflow for `github_ci_status.py`

Add a new low-risk Agent OS workflow:

- `github_ci_status_collect`

It should:

- run `python3 tools/github_ci_status.py`
- persist the workflow report
- not send alerts directly
- not own delivery/escalation

At that point, `prod-observe` would cover:

- `daily_ops_state_lint`
- `product_progress_snapshot`
- `github_ci_status_collect`

### Phase 3 — compare outputs

Run both paths in parallel for a fixed window:

- internal `Deploy log capture and status audit`
- Agent OS `github_ci_status_collect`

Acceptance criteria:

- identical or equivalent `deploy-status.json`
- equivalent regression watchdog output
- no missing alerts
- no production health regression

### Phase 4 — extract policy wrapper

Create a smaller wrapper responsible only for:

- reading produced artifacts
- applying ownership policy
- appending to `daily-summary.md`
- deciding delivery mode

Possible future ownership:

- still internal OpenClaw cron
- or a new Agent OS policy workflow

### Phase 5 — retire the old monolithic job

Only when phases 2–4 are validated should the internal `Deploy log capture and status audit` be replaced or disabled.

## Proposed next safe implementation

The next safe implementation step is:

1. add `github_ci_status_collect` to `control-plane/config/workflow_registry.json`
2. do **not** add it to `prod-observe` immediately
3. validate it manually first
4. then decide whether to schedule it in `prod-observe`

This keeps the blast radius small.

## What should not be done yet

Do not, in one step:

- disable the internal deploy audit job
- move alert ownership to Agent OS
- move delivery/escalation to Agent OS
- combine CI mutation/remediation with observation

## Decision summary

The migration path for deploy audit should be:

- first split **collection** from **policy**
- then migrate **collection**
- only later migrate **policy/orchestration**

That is the only low-risk path consistent with the current production state.
