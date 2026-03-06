# Agent OS Prod Autopilot SLA Prep - 2026-03-06

## Scope

Prepare the next deterministic host-side migration slice for `Daily autopilot SLA tracker` without disabling the current internal OpenClaw cron yet.

## What was added

- `scripts/autopilot_sla_tracker.py`
- `control-plane/scripts/prod_autopilot_sla_cycle.sh`
- `control-plane/scripts/install_prod_autopilot_sla_cron.sh`

## Manual validation

Executed:

- `/home/leandro/openclaw-container/control-plane/scripts/prod_autopilot_sla_cycle.sh`

Observed:

- pre-run `Gateway Health OK`
- `autopilot-sla.json` updated
- `autopilot-sla.md` updated
- dashboard sync executed successfully
- post-run `Gateway Health OK`

Relevant output:

```text
✅ Synced: ops/multiagent/delivery/autopilot-sla.json → projects/site-lf-solucoes/dashboards/data/autopilot-sla.json
✅ Synced: ops/multiagent/delivery/handoff-master.json → projects/site-lf-solucoes/dashboards/data/handoff.json
✅ Updated timestamp: projects/site-lf-solucoes/dashboards/data/kanban.json
autopilot_sla_json=/home/leandro/clawd/ops/multiagent/delivery/autopilot-sla.json
autopilot_sla_md=/home/leandro/clawd/ops/multiagent/delivery/autopilot-sla.md
```

## Current host cron block

Installed in parallel, without disabling the internal job:

```cron
# === OpenClaw Agent OS Prod autopilot SLA ===
45 22 * * * flock -n /home/leandro/openclaw/runtime/agentos/prod-autopilot-sla.lock /home/leandro/openclaw-container/control-plane/scripts/prod_autopilot_sla_cycle.sh >> /home/leandro/openclaw/logs/agentos-prod-autopilot-sla.log 2>&1
# === /OpenClaw Agent OS Prod autopilot SLA ===
```

## Current migration status

- host-side SLA slice: prepared and manually validated
- host-side cron: installed
- internal OpenClaw cron `Daily autopilot SLA tracker`: still enabled

## Why the internal cron was kept enabled

The current plan requires an equivalence window first.

Only after observing scheduled host-side runs should the internal cron be disabled.

## Next gate

Observe the first scheduled host-side run at `22:45` local time, compare generated `autopilot-sla.json/.md`, and only then decide whether to disable the internal OpenClaw cron scheduled for `22:50`.
