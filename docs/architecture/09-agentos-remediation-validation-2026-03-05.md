# Agent OS Remediation Validation (2026-03-05)

Scope: validate the remediation work applied after `08-agentos-audit-report-2026-03-05.md`.

## Result

- Agent OS control-plane foundation: PASS
- Production runtime cutover to Agent OS scheduler: NOT APPLIED
- Recommendation: GO for candidate/green validation of the control-plane foundation, keep current production crons untouched until a dedicated rollout wave.

## Validation Table

| Item | Status | Evidence |
|---|---|---|
| B1 control-plane structure | PASS | `control-plane/policies/production_preflight_policy.json`, `control-plane/scripts/*.sh` |
| C3 retry/backoff persistence | PASS | `scripts/agentos.py` stores `state.nextRunAt`; unit test `test_retry_exhaustion_moves_task_to_needs_human` |
| D2 `task.handoff` support | PASS | `scripts/agentos.py` `handoff_task(...)`; events present in `/tmp/agentos_allow.db` |
| E1 Telegram envelope guards | PASS | `prepare_telegram_envelope()` + manual JSON redaction test |
| F1 preflight coverage | PASS | deny/allow scenarios plus log-tail, bind-loopback, multi-provider checks |
| F2 supervisor preflight enforcement | PASS | `Supervisor.cycle(...)` executes `execute_preflight(...)` and blocks denied tasks |
| G1 supervisor autonomous processing | PASS | supervisor persists planning tasks, blocks roots, escalates failed tasks |
| G2 planner/executor roles | PASS | `Planner` and `Executor` classes; role-tagged events |
| G3 evidence gate before completion | PASS | `complete_task(...)` validates acceptance evidence; unit test added |
| J1 safe mode runtime toggle | PASS | `load_supervisor_settings()` + `AGENTOS_SAFE_MODE` override |

## Commands Executed

```bash
python3 -m unittest tests.unit.test_agentos
./scripts/test_gate.sh
python3 scripts/agentos.py validate-schemas
python3 scripts/agentos.py init-db --db /tmp/agentos_audit.db
python3 scripts/agentos.py enqueue-demo --db /tmp/agentos_audit.db --kind policy_change --title 'Denied wave demo' --infra --policy
python3 scripts/agentos.py supervisor-cycle --db /tmp/agentos_audit.db --unsafe-mode
python3 scripts/agentos.py init-db --db /tmp/agentos_allow.db
python3 scripts/agentos.py enqueue-demo --db /tmp/agentos_allow.db --kind policy_change --title 'Allowed wave demo' --policy
python3 scripts/agentos.py supervisor-cycle --db /tmp/agentos_allow.db --unsafe-mode
python3 scripts/agentos.py envelope --header '[Stephen][AUDIT]' --artifact-ref artifact://json --file /tmp/agentos_large.json
AGENTOS_SAFE_MODE=0 python3 scripts/agentos.py supervisor-cycle --db /tmp/agentos_safe.db
```

## Key Outputs

### Unit and gate tests

```text
python3 -m unittest tests.unit.test_agentos
Ran 11 tests in 1.468s
OK

./scripts/test_gate.sh
Ran 20 tests in 1.690s
OK
Ran 6 regression tests
OK
```

### Preflight deny path

```json
{
  "action": "processed_sensitive_queue",
  "blockedTasks": ["9a66d8d9-9765-455e-84cf-59ae83981ab8"],
  "derivedTasks": []
}
```

### Preflight allow path

```json
{
  "action": "processed_sensitive_queue",
  "derivedTasks": [
    {
      "kind": "planning",
      "title": "Plan execution for Allowed wave demo"
    }
  ],
  "blockedTasks": ["189f281f-0302-4336-94fc-4842b3e1d783"]
}
```

### Handoff evidence

Query against `/tmp/agentos_allow.db` returned event sequence:

```text
task.created
task.created
task.handoff
task.blocked
```

### Telegram envelope sanitization

```json
{
  "parts": [
    "[Stephen][AUDIT][part 1/1]\n\nLarge JSON payload omitted. See artifact://json."
  ]
}
```

## Notes

- This validation covers the local control-plane implementation only.
- The current production container remains untouched; no cron/autopilot wiring was changed here.
- The next release wave should focus only on integrating selected low-risk workflows into this control-plane.
