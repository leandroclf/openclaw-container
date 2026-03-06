# Agent OS Green Scheduled Observation Evidence

Date: 2026-03-06
Scope: install and validate host-side WSL cron scheduling for Agent OS observation on `openclaw-next` only.

## Files added

- `control-plane/scripts/green_observe_cycle.sh`
- `control-plane/scripts/install_green_observe_cron.sh`
- `docs/operations/AGENTOS_GREEN_SCHEDULED_OBSERVATION.md`

## Registry state

The Green observation cycle runs these workflows in order:

- `daily_ops_state_lint`
- `daily_summary_rotation`
- `product_progress_snapshot`

## Commands executed

```bash
./control-plane/scripts/green_observe_cycle.sh
service cron status
./control-plane/scripts/install_green_observe_cron.sh
crontab -l
./scripts/test_gate.sh
```

## Manual dry run

The observation cycle completed successfully against `openclaw-next` and `~/clawd-next`.

Workflow task IDs created during the dry run:

- `daily_ops_state_lint` -> `280559e4-4247-45b3-99e9-6d8b8e347d25`
- `daily_summary_rotation` -> `c0d8b335-340b-4be3-9676-3d5584ba5d01`
- `product_progress_snapshot` -> `5780d332-e263-4c18-b911-d69646f0266d`

Runtime health observed in the same cycle:

- before execution: `Gateway Health OK`, `Telegram: not configured`
- after execution: `Gateway Health OK`, `Telegram: not configured`

SQLite DB written by the cycle:

- `~/openclaw-next/runtime/agentos/green-observe.db`

## Cron installation

Cron daemon state:

- `cron.service` -> `active (running)`

Installed managed block:

```cron
# === OpenClaw Agent OS Green observe ===
12,32,52 * * * * flock -n /home/leandro/openclaw-next/runtime/agentos/green-observe.lock /home/leandro/openclaw-container/control-plane/scripts/green_observe_cycle.sh >> /home/leandro/openclaw-next/logs/agentos-green-observe.log 2>&1
# === /OpenClaw Agent OS Green observe ===
```

Log target:

- `~/openclaw-next/logs/agentos-green-observe.log`

## Test gate

- `./scripts/test_gate.sh` -> passed
- Unit tests:
  - `Ran 22 tests`
  - `OK`
- Regression tests:
  - `Ran 6 tests`
  - `OK`

## Operational conclusion

- The Green scheduled observation path is installed and isolated from production.
- The scheduler uses WSL cron, not OpenClaw internal cron, which keeps host-side control explicit.
- Production cron behavior was not modified.
