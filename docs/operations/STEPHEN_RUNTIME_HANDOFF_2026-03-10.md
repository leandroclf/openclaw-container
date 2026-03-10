# Stephen Runtime Handoff - 2026-03-10

Purpose: provide a short operational handoff for the running production
environment after the full Agent OS migration.

## Current production facts

- Runtime container:
  - `openclaw`
- OpenClaw version:
  - `2026.3.8`
- Gateway:
  - bind `loopback`
  - port `18789`
- Telegram:
  - enabled in production
  - allowlist and pairing still enforced

## What changed operationally

### Production now runs on a host-side Agent OS control plane

Active host-side lanes:

- `prod-observe`
  - `daily_ops_state_lint`
  - `product_progress_snapshot`
  - `github_ci_status_collect`
- `prod-policy-audit`
  - deploy audit policy wrapper
- `prod-autopilot-sla`
  - deterministic SLA generation
- `prod-idle-watchdog-observe`
- `prod-idle-watchdog-policy`
- `prod-idle-watchdog-handoff`
- `prod-idle-watchdog-consumer`
- `prod-idle-watchdog-execution`

### Internal OpenClaw cron kept active

- `Autopilot sequential delivery cycle`
- `Daily summary rotation`
- `Weekly code evolution KPI audit`
- `Weekly specialist productivity audit`

### Internal OpenClaw cron removed from the main execution path

- `Autopilot idle watchdog`
- `Deploy log capture and status audit`
- `Daily ops state lint`
- `Daily autopilot SLA tracker`

## Ownership rules

- Host-side Agent OS owns:
  - collection
  - policy wrapping
  - SLA generation
  - idle watchdog chain
- Internal OpenClaw cron still owns:
  - sequential delivery execution
  - daily summary rotation
  - weekly audits

## Commands to trust first

Use these before diagnosing anything else:

```bash
docker exec openclaw openclaw --profile prod gateway health
tail -n 200 ~/openclaw/logs/openclaw-$(date +%F).log
tail -n 200 ~/openclaw/logs/agentos-prod-observe.log
tail -n 200 ~/openclaw/logs/agentos-prod-policy-audit.log
tail -n 200 ~/openclaw/logs/agentos-prod-idle-watchdog-execution.log
```

## Commands that now represent source-of-truth operations

```bash
./scripts/install_cron.sh
./scripts/daily_maintenance.sh
./scripts/update.sh
./scripts/backup.sh
```

## Files to read before changing behavior

1. `docs/operations/OPERATIONS_DOC_INDEX_2026-03-10.md`
2. `docs/operations/AGENTOS_FULL_CUTOVER_2026-03-10.md`
3. `docs/operations/PRODUCTION_CHANGE_POLICY.md`
4. `docs/operations/PROMOTION_ROLLBACK_CHECKLIST.md`
5. `docs/operations/IDLE_WATCHDOG_CUTOVER_PLAYBOOK_2026-03-06.md`

## Constraints that still apply

- Do not write product code into `openclaw-container`.
- Do not reuse candidate patterns from Green; Green is gone.
- Do not reactivate old internal jobs unless the rollback playbook says to.
- Do not change Telegram token usage or binding rules.
- Do not bypass host-side cron ownership for collection/policy/SLA/watchdog.

## If a failure appears

1. Confirm `gateway health`.
2. Inspect the relevant host-side lane log.
3. Inspect the matching runtime artifact under `~/openclaw/runtime/agentos`.
4. Follow `PROMOTION_ROLLBACK_CHECKLIST.md` and `IDLE_WATCHDOG_CUTOVER_PLAYBOOK_2026-03-06.md`.

## Message template for Stephen

```text
Stephen, absorb the current production state from:
- docs/operations/OPERATIONS_DOC_INDEX_2026-03-10.md
- docs/operations/AGENTOS_FULL_CUTOVER_2026-03-10.md
- docs/operations/STEPHEN_RUNTIME_HANDOFF_2026-03-10.md

Operational facts:
- Production runs on OpenClaw 2026.3.8 in container `openclaw`
- Host-side Agent OS now owns collection, policy audit, SLA, and idle-watchdog chain
- Internal OpenClaw keeps only sequential delivery, daily summary rotation, and weekly audits
- Do not assume Green still exists
- Do not reactivate old internal watchdog/deploy-audit/SLA jobs

Before acting, validate:
- docker exec openclaw openclaw --profile prod gateway health

If you diagnose issues, use host-side lane logs and runtime artifacts as the
primary evidence source.
```
