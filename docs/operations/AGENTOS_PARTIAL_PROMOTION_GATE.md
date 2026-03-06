# Agent OS Partial Promotion Gate

Purpose: define the first production promotion slice for Agent OS after Green validation, without executing the promotion in this document.

## Current evidence baseline

Promotion planning is based on these already validated Green artifacts:

- `docs/operations/AGENTOS_GREEN_WAVE3_EVIDENCE.md`
- `docs/operations/AGENTOS_GREEN_SOAK_EVIDENCE.md`
- `docs/operations/AGENTOS_GREEN_LONG_SOAK_EVIDENCE.md`
- `docs/operations/AGENTOS_GREEN_WAVE4_PRODUCT_PROGRESS_EVIDENCE.md`
- `docs/operations/AGENTOS_GREEN_SCHEDULED_OBSERVATION_EVIDENCE.md`
- `docs/operations/AGENTOS_GREEN_SCHEDULED_OBSERVATION_RUN_2026-03-06.md`
- `docs/operations/AGENTOS_GREEN_SCHEDULED_OBSERVATION_REPEATABILITY_2026-03-06.md`

## Promotion principle

Do **not** promote the full Agent OS stack in one step.

The first production promotion slice must be:

- host-side
- shadow/observe-oriented
- reversible with one cron block removal
- isolated from Telegram delivery changes
- isolated from product repo writeback logic
- isolated from OpenClaw internal cron/autopilot replacement

## Recommended first production slice

Promote only a **production-side scheduled observation lane** equivalent to the Green lane, with these constraints:

- scheduler remains WSL cron
- target container remains `openclaw`
- workspace remains `~/clawd`
- no Telegram delivery from the Agent OS lane
- no code-delivery tasks
- no product repo writes
- no replacement of existing production cron jobs yet

### Allowed workflows in slice 1

- `daily_ops_state_lint`
- `daily_summary_rotation`
- `product_progress_snapshot`

### Forbidden in slice 1

- CI remediation workflows
- repo mutation workflows
- any workflow that opens PRs, commits, or pushes
- any task type that requires `policy_change`, `routing_change`, `auth_change`, or runtime mutation
- any change to existing production cron entries beyond adding a new isolated block

## Gate decision matrix

### GO only if all are true

- [ ] `docker context show` is `default`
- [ ] production `openclaw` health is `OK`
- [ ] Green scheduled observation has at least 3 successful automatic runs
- [ ] Green DB shows no `blocked`, `failed`, or retry-heavy state
- [ ] `./scripts/test_gate.sh` passes on the repo state to be promoted
- [ ] rollback command is prepared and tested syntactically
- [ ] production cron block for current operations remains unchanged
- [ ] the new production Agent OS block writes to its own DB/log targets

### NO-GO if any of these occur

- [ ] candidate shows inconsistent health after scheduled runs
- [ ] candidate log shows overlap, lock failures, or truncated execution
- [ ] candidate DB shows retry/backoff or hidden blocked tasks
- [ ] production already has an overlapping scheduler for the same three workflows
- [ ] promotion would require changing Telegram behavior
- [ ] promotion would mix observation and mutation in the same wave

## Proposed production wiring for slice 1

Use a dedicated production Agent OS observation block, analogous to Green but with production paths.

### Proposed runtime paths

- DB: `~/openclaw/runtime/agentos/prod-observe.db`
- Log: `~/openclaw/logs/agentos-prod-observe.log`
- Lock: `~/openclaw/runtime/agentos/prod-observe.lock`

### Proposed schedule

Start conservatively:

- `17,47 * * * *`

This avoids overlapping with current Green runs (`12,32,52`) and avoids exact collision with the healthcheck schedule (`*/15`).

## Pre-promotion checklist

Run and capture all of these before any promotion:

```bash
docker context ls && docker context show
docker ps --filter name=openclaw
docker exec openclaw openclaw --profile prod gateway health
docker exec openclaw openclaw --profile prod status
tail -n 200 ~/openclaw/logs/openclaw-$(date +%F).log
tail -n 200 ~/openclaw-next/logs/agentos-green-observe.log
python3 - <<'PY'
import sqlite3, json
conn = sqlite3.connect('/home/leandro/openclaw-next/runtime/agentos/green-observe.db')
cur = conn.cursor()
print(json.dumps({
  "tasks": cur.execute('select kind, status, count(*) from tasks group by kind, status order by kind, status').fetchall(),
  "events_total": cur.execute('select count(*) from events').fetchone()[0],
  "artifacts": cur.execute('select kind, count(*) from artifacts group by kind order by kind').fetchall(),
}, indent=2))
PY
./scripts/test_gate.sh
```

## Promotion execution model for slice 1

When approved, promotion should consist only of:

1. installing a new production Agent OS cron block
2. pointing it to production-only DB/log paths
3. keeping the existing production cron block active
4. monitoring for one observation window
5. stopping immediately if any regression appears

No container restart is required for slice 1.

## Rollback for slice 1

Rollback must be one-step and non-destructive:

```bash
crontab -l | sed '/^# === OpenClaw Agent OS Prod observe ===$/,/^# === \\/OpenClaw Agent OS Prod observe ===$/d' | crontab -
```

Then validate:

```bash
docker exec openclaw openclaw --profile prod gateway health
tail -n 200 ~/openclaw/logs/agentos-prod-observe.log
```

Preserve:

- `~/openclaw/runtime/agentos/prod-observe.db`
- `~/openclaw/logs/agentos-prod-observe.log`

for post-mortem.

## Exit criteria for slice 1

Slice 1 is considered successful only if:

- production stays healthy during at least 3 automatic production-side observation runs
- no Telegram regression occurs
- no duplicate scheduler conflict appears
- the new production DB/log artifacts remain consistent with the Green lane pattern

Only after that should the next gate be considered:

- replacing or instrumenting parts of the existing production cron logic
- enabling additional low-risk workflows
- considering mutation-capable Agent OS flows
