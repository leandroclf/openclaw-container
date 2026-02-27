# Risk Register and Rollback Playbook

This register tracks main failure modes for the proposed stack and defines
immediate rollback actions.

## Risk matrix

| ID | Risk | Probability | Impact | Early signal | Mitigation | Rollback |
|---|---|---|---|---|---|---|
| R1 | Host resource saturation (RAM/CPU/IO) | Medium | High | OpenClaw latency and timeouts spike | Resource limits, retention tuning, phased enablement | Stop latest added profile/services first |
| R2 | Queue backlog in async layer | Medium | Medium | JetStream pending grows continuously | Backpressure, consumer autoscaling limits, dead-letter design | Disable async route and run direct execution |
| R3 | Policy false deny | Medium | High | Valid operations denied by policy | Start in audit mode, policy tests in CI | Disable policy enforcement, keep decision logs |
| R4 | Secret retrieval failure | Low/Medium | High | Auth errors to providers, startup failures | AppRole rotation drills, health probes | Revert to known-good env source and restart affected service |
| R5 | Telemetry overhead causes instability | Medium | Medium | Memory pressure, high disk write | Limit scrape intervals, tune retention/cardinality | Stop observability profile except minimal logs |
| R6 | Cache poisoning/stale outputs | Medium | Medium | Wrong repeated answers after state changes | Key scoping + short TTL for mutable tasks | Disable cache reads and purge key namespace |
| R7 | Isolation runtime incompatibility | Low/Medium | Medium | Commands fail only under runsc | Progressive rollout by worker type | Move impacted workload back to default runtime |
| R8 | Eval suite drift (false failures) | Medium | Low/Medium | Sudden score drop without product regressions | Version prompts/datasets, calibrate thresholds | Mark suite non-blocking and investigate |
| R9 | Secrets leaked in logs | Low | High | Tokens appear in runtime logs | Masking filters, logger guards | Rotate affected secrets immediately |
| R10 | Cross-repo coupling regression | Medium | Medium | Infra changes depend on workspace internals | Strict repo contract + mounted interface only | Revert coupling commit and restore repo boundaries |

## Rollback priorities

When incident happens, rollback in this order:
1. Disable newest/last changed layer.
2. Restore prior config snapshot.
3. Re-validate OpenClaw core health and channel response.
4. Capture incident record before retrying rollout.

## Mandatory pre-change artifacts

Before each production change:
- Config backup (OpenClaw and service config).
- Last known good compose/profile command.
- Health command bundle prepared.
- Incident note template ready.

## Incident note template

```text
Timestamp:
Change introduced:
Observed symptom:
Immediate impact:
Rollback executed:
Time to recover:
Root cause:
Follow-up action:
```

## Non-negotiable safety checks

- Never rotate all provider credentials at once.
- Never migrate all cron jobs to a new orchestrator in one step.
- Never enforce policy before at least one audit-only cycle window.
- Never remove the current working path before proving the replacement.
