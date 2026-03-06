# Agent OS Production Observe Preparation

Purpose: prepare the first production Agent OS slice without activating it yet.

This preparation adds the scripts needed for a host-side production observation lane that mirrors the validated Green lane.

## Scope of slice 1

Allowed workflows:

- `daily_ops_state_lint`
- `product_progress_snapshot`

Out of scope:

- `daily_summary_rotation` remains owned by the internal once-daily OpenClaw cron
- Telegram delivery changes
- product repo writes
- PR/commit/push flows
- replacement of existing production cron jobs

## Files prepared

- `control-plane/scripts/prod_observe_cycle.sh`
- `control-plane/scripts/install_prod_observe_cron.sh`

## Proposed production paths

- DB: `~/openclaw/runtime/agentos/prod-observe.db`
- Lock: `~/openclaw/runtime/agentos/prod-observe.lock`
- Log: `~/openclaw/logs/agentos-prod-observe.log`

## Proposed production schedule

- `17,47 * * * *`

Rationale:

- avoids overlap with the validated Green lane (`12,32,52`)
- avoids exact alignment with the existing `*/15` healthcheck

## Manual install command

Do not run this until promotion is explicitly approved:

```bash
/home/leandro/openclaw-container/control-plane/scripts/install_prod_observe_cron.sh
```

## Manual dry run command

Use only when promotion approval exists and production baseline has been captured:

```bash
/home/leandro/openclaw-container/control-plane/scripts/prod_observe_cycle.sh
```

## Rollback command

```bash
crontab -l | sed '/^# === OpenClaw Agent OS Prod observe ===$/,/^# === \\/OpenClaw Agent OS Prod observe ===$/d' | crontab -
```

## Required gate before activation

Activation must satisfy:

- `docs/operations/AGENTOS_PARTIAL_PROMOTION_GATE.md`
- `docs/operations/PROMOTION_ROLLBACK_CHECKLIST.md`
