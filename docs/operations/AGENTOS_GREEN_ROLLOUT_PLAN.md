# Agent OS Green Rollout Plan

Purpose: validate the local Agent OS control-plane foundation in a Green candidate without touching the current production `openclaw` runtime.

## Scope

This plan does **not** replace the current production autopilot/cron stack in one step.
It validates only one low-risk integration wave at a time.

## Preconditions

- Production `openclaw` remains online and healthy.
- Candidate uses isolated paths:
  - `~/openclaw-next/*`
  - `~/clawd-next`
- Candidate does not reuse the production Telegram bot token.
- Docker context is confirmed before any action.

## Wave 1 (recommended)

Goal: validate Agent OS in observe/assist mode only.

Enable only:
- schema validation
- SQLite init
- event emission
- supervisor `safeMode=true`
- one synthetic queue flow for `policy_change`

Do **not** enable yet:
- production cron replacement
- code-delivery task completion
- automatic writeback into product repos
- Telegram delivery of Agent OS events

### Validation commands

```bash
docker context ls
docker context show
./control-plane/scripts/validate_schema.sh
./control-plane/scripts/init_db.sh
python3 scripts/agentos.py enqueue-demo --kind policy_change --title 'green-wave-1' --policy
python3 scripts/agentos.py supervisor-cycle --safe-mode
python3 -m unittest tests.unit.test_agentos
./scripts/test_gate.sh
```

Acceptance:
- all commands succeed
- safe mode emits progress events only
- no production container change
- no candidate Telegram polling conflict

## Wave 2

Goal: validate preflight enforcement + planning handoff in candidate.

Enable:
- supervisor `safeMode=false` in candidate only
- deny path for forbidden wave
- allow path for permitted wave
- persisted `planning` tasks and `task.handoff`

Validation:

```bash
python3 scripts/agentos.py init-db --db /tmp/agentos_wave2.db
python3 scripts/agentos.py enqueue-demo --db /tmp/agentos_wave2.db --kind policy_change --title 'deny-demo' --infra --policy
python3 scripts/agentos.py supervisor-cycle --db /tmp/agentos_wave2.db --unsafe-mode
python3 scripts/agentos.py enqueue-demo --db /tmp/agentos_wave2.db --kind policy_change --title 'allow-demo' --policy
python3 scripts/agentos.py supervisor-cycle --db /tmp/agentos_wave2.db --unsafe-mode
```

Acceptance:
- forbidden wave -> blocked with deny reason
- allowed wave -> planning task persisted + handoff event persisted

## Wave 3

Goal: wire one low-risk existing workflow to Agent OS.

Recommended first integration target:
- daily ops state lint
- or daily summary rotation

Reason:
- low blast radius
- no product repo writes
- easy rollback

Acceptance:
- workflow emits Agent OS task/event records
- existing production health remains unchanged
- rollback is one config/script reversion only

## Promotion gate

Promote any Agent OS integration wave only if:
- production baseline remains green
- candidate tests pass
- no Telegram conflict exists
- rollback commands are already prepared

## Rollback

- stop candidate wiring only
- keep production `openclaw` unchanged
- preserve `control-plane/state/` and `control-plane/artifacts/` for post-mortem
