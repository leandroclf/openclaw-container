# Agent OS Migration Audit Report (2026-03-05)

Scope: audit-only review of the `OpenClaw -> Agent OS` migration against `docs/architecture/OpenClaw_AgentOS_Migration.md`.

Method:
- No assumptions were accepted without a file or command proof.
- Evidence was collected from the repository, local SQLite state, and the running `openclaw` container.
- Secrets were redacted or omitted.

## Build Manifest

- Commit SHA: `bcb08662130a2770d80c752809f58c6fe2d721db`
- Branch: `main`
- Runtime OpenClaw version: `2026.3.2`
- Docker image ID: `sha256:8975794a29d21c1b14f89b30ce9db4ef9f0ffa569ac10abe5a0c49c934fbfbbd`
- Change set relative to current `main` worktree:
  - tracked modified: `.gitignore`, `README.md`, `docs/architecture/README.md`
  - untracked Agent OS assets: `control-plane/...`, `scripts/agentos.py`, `tests/unit/test_agentos.py`, `docs/architecture/06-openclaw-workspace-control-plane.md`, `docs/architecture/OpenClaw_AgentOS_Migration.md`

Commands used:

```bash
git rev-parse HEAD
git branch --show-current
git status --short --untracked-files=all
docker exec openclaw openclaw --version
docker image inspect openclaw-secure:latest --format '{{.Id}}'
```

## Summary Table

| Item | Status | Notes |
|---|---|---|
| A1 | PASS | Build manifest collected from git + container + image |
| A2 | PASS | ACP/ACPX effective config confirmed from runtime |
| A3 | PASS | No product repo code detected in migration paths |
| B1 | FAIL | `control-plane/policies/` and `control-plane/scripts/` are missing |
| B2 | PASS | Schemas exist and include required core routing/event fields |
| C1 | PASS | SQLite DB initializes cleanly with `tasks/events/artifacts` + indexes |
| C2 | PASS | Lease claim/heartbeat/expire/reclaim works end-to-end |
| C3 | FAIL | Retry exists, but no real delayed backoff scheduling is persisted/enforced |
| D1 | PASS | Central emitter writes DB + JSONL + artifact record |
| D2 | FAIL | `task.handoff` support is absent |
| E1 | FAIL | Chunking exists, but no raw-JSON guard or stacktrace truncation policy |
| F1 | FAIL | Preflight is executable, but baseline/log/bind/auth-wave coverage is incomplete |
| F2 | FAIL | Supervisor does not execute preflight or block sensitive tasks on preflight failure |
| G1 | FAIL | Supervisor is not a real autonomous loop yet |
| G2 | FAIL | No explicit Planner/Executor role separation or role tagging |
| G3 | FAIL | No evidence/acceptance gate before `task.completed` |
| H1 | PASS | `kind -> objective` mapping exists and is wired to `model_router.py` |
| H2 | PASS | `requestedAgent` and `effectiveAgent` are recorded with reason |
| I1 | PASS | Minimum unit test plan exists and passes |
| I2 | PASS | Promotion/rollback docs cover health, test gate, soak window |
| J1 | FAIL | Safe mode exists only as CLI/config stub, not as enforced runtime toggle |
| J2 | PASS | Blue/Green rollback procedure is documented; artifacts are preserved locally |

## Detailed Evidence

### A1 - Build manifest
Status: PASS

Evidence:
- `git rev-parse HEAD` -> `bcb08662130a2770d80c752809f58c6fe2d721db`
- `git branch --show-current` -> `main`
- `git status --short --untracked-files=all` showed migration files only under control-plane/scripts/docs, for example:
  - `?? control-plane/config/routing_rules.json`
  - `?? control-plane/schemas/task.schema.json`
  - `?? scripts/agentos.py`
  - `?? tests/unit/test_agentos.py`
- `docker exec openclaw openclaw --version` -> `2026.3.2`
- `docker image inspect openclaw-secure:latest --format '{{.Id}}'` -> `sha256:8975794a29d21c1b14f89b30ce9db4ef9f0ffa569ac10abe5a0c49c934fbfbbd`

Risk if FAIL:
- n/a

Minimal fix suggested:
- n/a

### A2 - ACP/ACPX runtime state
Status: PASS

Evidence:
- `docker exec openclaw openclaw --profile prod config get acp` returned:

```json
{
  "dispatch": { "enabled": true },
  "backend": "acpx",
  "defaultAgent": "gemini",
  "allowedAgents": ["gemini"],
  "maxConcurrentSessions": 2
}
```

- `docker exec openclaw openclaw --profile prod config get plugins.entries.acpx` returned:

```json
{
  "enabled": true,
  "config": {
    "permissionMode": "approve-reads",
    "nonInteractivePermissions": "deny",
    "queueOwnerTtlSeconds": 15,
    "command": "/home/node/.openclaw/acpx-runtime/node_modules/.bin/acpx",
    "expectedVersion": "0.1.15"
  }
}
```

Historical snapshot: the current `acpx` schema is smaller in `2026.4.24` and no longer accepts `command` / `expectedVersion` in `plugins.entries.acpx.config`.

Risk if FAIL:
- n/a

Minimal fix suggested:
- n/a

### A3 - Repo boundaries
Status: PASS

Evidence:
- `git status --short --untracked-files=all` contains no changes under `projects/`.
- All migration files are inside:
  - `control-plane/`
  - `scripts/agentos.py`
  - `tests/unit/test_agentos.py`
  - docs files

Risk if FAIL:
- Product code could be polluted by control-plane changes.

Minimal fix suggested:
- Keep Agent OS files isolated to `control-plane/`, `scripts/`, `tests/`, `docs/`.

### B1 - Control-plane directory structure
Status: FAIL

Expected minimum:
- `control-plane/schemas/...`
- `control-plane/state/`
- `control-plane/artifacts/...`
- `control-plane/policies/`
- `control-plane/scripts/`

Evidence:
- `find control-plane -maxdepth 2 -type d | sort` returned only:
  - `control-plane/artifacts`
  - `control-plane/config`
  - `control-plane/schemas`
  - `control-plane/state`
- `control-plane/policies/` is missing.
- `control-plane/scripts/` is missing.

Risk if FAIL:
- Policy logic and control-plane operational entrypoints remain coupled to `scripts/agentos.py`, making the migration incomplete and harder to evolve safely.

Minimal fix suggested:
- Add:
  - `control-plane/policies/production_preflight_policy.json` or equivalent
  - `control-plane/scripts/README.md` or extracted wrappers for `init-db`, `validate-schema`, `preflight`, `supervisor`

### B2 - Schema presence and format
Status: PASS

Evidence:
- `control-plane/schemas/task.schema.json` requires `schemaVersion`, `taskId`, `correlationId`, `routing`, `acceptance`, `state`, `timestamps`.
- `control-plane/schemas/task.schema.json` defines `routing.requestedAgent` and `routing.effectiveAgent`.
- `control-plane/schemas/event.schema.json` requires `correlationId`, `taskId`, `eventType`, `evidenceRefs`.
- `control-plane/schemas/preflight.schema.json` requires `changeWave` and `allowedToProceed`.
- Runtime validators exist in `scripts/agentos.py:84-176`.

Risk if FAIL:
- Event/task compatibility would drift and break queue/supervisor evolution.

Minimal fix suggested:
- n/a

### C1 - SQLite initialization and tables
Status: PASS

Evidence:
- `python3 scripts/agentos.py init-db` -> initialized `control-plane/state/agentos.db`
- Schema query against SQLite returned:
  - table `tasks`
  - table `events`
  - table `artifacts`
  - indexes `idx_tasks_status_priority`, `idx_tasks_lease_until`, `idx_events_task_created`
- DDL is defined in `scripts/agentos.py:354-456` and DB bootstrap earlier in the file.

Risk if FAIL:
- No durable queue or event log.

Minimal fix suggested:
- n/a

### C2 - Lease/TTL flow
Status: PASS

Evidence:
Manual execution:

```bash
python3 scripts/agentos.py enqueue-demo --kind code_impl --title 'Lease flow audit demo'
python3 scripts/agentos.py claim-next --worker-id audit-worker --lease-seconds 2
python3 scripts/agentos.py heartbeat --task-id 10eb442e-d031-4995-b3a3-05ad8b2bd0cb --worker-id audit-worker --lease-seconds 5
sleep 6 && python3 scripts/agentos.py expire-leases
python3 scripts/agentos.py claim-next --worker-id audit-worker-2 --lease-seconds 10
```

Observed outputs:
- claim set `leaseOwner=audit-worker`, `leaseUntil=...`
- heartbeat extended `leaseUntil`
- `expire-leases` returned `{"expired": 1}`
- reclaim moved lease to `audit-worker-2`

Event log for the same task:
- `task.created`
- `task.claimed`
- `task.progress`
- `task.retry_scheduled`
- `task.claimed`

Unit test also covers the same flow in `tests/unit/test_agentos.py:39-58`.

Risk if FAIL:
- Work stealing and recovery after worker death would not function.

Minimal fix suggested:
- n/a

### C3 - Retry/backoff/needs_human
Status: FAIL

Evidence:
- `scripts/agentos.py:588-620` increments attempts and emits:
  - `task.retry_scheduled`
  - `task.needs_human`
  - `task.failed`
- Manual test with `maxRetries=1` ended in `needs_human` with events:

```json
{
  "after_first_fail_status": "queued",
  "after_second_fail_status": "needs_human",
  "final_db_status": "needs_human",
  "attempts": 2,
  "events": [
    "task.created",
    "task.claimed",
    "task.retry_scheduled",
    "task.claimed",
    "task.needs_human"
  ]
}
```

- However, no actual delayed backoff state is stored. There is no `next_run_at` field in `tasks`, and `task.retry_scheduled` only carries `retryInSeconds` in the event payload. Requeue is immediate.

Risk if FAIL:
- Repeated transient failures can hot-loop and consume budget/log volume faster than intended.

Minimal fix suggested:
- Add `next_run_at` to `tasks`, include it in claim selection, and set it on retry.

### D1 - Central EventEmitter
Status: PASS

Evidence:
- `scripts/agentos.py:445-457`:
  - validates/builds event
  - inserts into SQLite via `_insert_event`
  - appends daily JSONL via `_append_event_jsonl`
  - records artifact via `_insert_artifact`
- Real JSONL evidence in `control-plane/artifacts/events/2026-03-06.jsonl`
- Example line:

```json
{"eventVersion":"2026-03-05.1","eventType":"task.completed",...,"evidenceRefs":["control-plane/README.md","/home/leandro/openclaw-container/control-plane/artifacts/tasks/5879660f-d887-4cfd-bf89-0c8ff7daa78d.json"]}
```

Risk if FAIL:
- No append-only audit trail.

Minimal fix suggested:
- n/a

### D2 - Mandatory event types
Status: FAIL

Evidence:
- Present in code and/or emitted:
  - `task.created` (`scripts/agentos.py:465`)
  - `task.claimed` (`scripts/agentos.py:514`)
  - `task.progress` (`scripts/agentos.py:532`)
  - `task.blocked` (`scripts/agentos.py:645`)
  - `task.failed` (`scripts/agentos.py:614`)
  - `task.retry_scheduled` (`scripts/agentos.py:554`, `606`)
  - `task.needs_human` (`scripts/agentos.py:610`)
  - `task.completed` (`scripts/agentos.py:581`)
- Missing:
  - `task.handoff` is not present in `scripts/agentos.py` and not present in the JSONL artifacts.

Risk if FAIL:
- Planner/executor or cross-agent handoffs cannot be audited explicitly.

Minimal fix suggested:
- Add explicit `handoff_task(...)` helper and emit `task.handoff` with from/to agent, reason, and handoff evidence.

### E1 - Telegram envelope / anti message-too-long
Status: FAIL

Evidence:
- Chunking implementation exists in `scripts/agentos.py:757-798` with:
  - target limit `2800`
  - hard limit `3500`
  - stable header `[part x/y]`
- Manual simulation with a `5795` character file:

```bash
python3 scripts/agentos.py envelope --header '[Stephen][AUDIT]' --file /tmp/agentos_long_message.txt
```

returned `3` parts, all chunked with stable headers.
- Missing guards:
  - no detection/blocking of large raw JSON payloads
  - no truncation policy for stacktraces/logs to 3-5 lines
  - no artifact reference substitution for oversized diagnostics

Risk if FAIL:
- Telegram messages can still be noisy, leak too much raw diagnostic content, or exceed operational standards even when chunked.

Minimal fix suggested:
- Add a formatter layer before chunking to summarize JSON/log payloads and replace large bodies with artifact references.

### F1 - Executable preflight
Status: FAIL

Evidence:
- Preflight implementation exists in `scripts/agentos.py:806-879`.
- Allowed scenario:

```bash
python3 scripts/agentos.py preflight --touches-production --routing
```

returned `allowedToProceed=true`.
- Denied scenario:

```bash
python3 scripts/agentos.py preflight --touches-production --infra --policy
```

returned `allowedToProceed=false`, `denyReason=infra+policy`.
- Gaps against the requested minimum:
  - no `tail -n ...` log baseline check in preflight
  - no explicit bind loopback validation for candidate
  - no explicit `auth multi-provider` deny rule

Risk if FAIL:
- Sensitive rollout tasks can pass preflight without key production/candidate invariants being checked.

Minimal fix suggested:
- Add checks for log tail capture, candidate bind validation, and `auth_multi_provider` deny rule.

### F2 - Preflight integrated into Supervisor
Status: FAIL

Evidence:
- `Supervisor.should_apply_preflight()` exists in `scripts/agentos.py:894-895`.
- `Supervisor.cycle()` in `scripts/agentos.py:916-932` only derives a `preflight_check` task and returns it.
- It does **not** call `execute_preflight()`.
- It does **not** persist derived tasks into SQLite.
- It does **not** block or fail the original sensitive task when the wave is invalid.
- Proof: `python3 scripts/agentos.py supervisor-cycle` on a queued `policy_change` task returned `derived_tasks_created`, but SQLite still had `0` rows with `kind='preflight_check'`.

Risk if FAIL:
- Sensitive tasks can proceed conceptually without any enforced gate.

Minimal fix suggested:
- Persist derived preflight tasks and/or execute preflight inline before allowing any sensitive task to be claimed/executed.

### G1 - Autonomous Supervisor -> Planner -> Executor loop
Status: FAIL

Evidence:
- `Supervisor.cycle()` only inspects queued tasks and returns a `SupervisorResult`.
- It does not:
  - observe `blocked` or `failed` tasks
  - apply retry/backoff policy itself
  - mark `needs_human`
  - persist derived tasks
  - execute or delegate tasks
- Safe-mode demo:

```bash
python3 scripts/agentos.py supervisor-cycle --safe-mode
```

returned `observe_only`.
- Non-safe-mode demo:

```bash
python3 scripts/agentos.py supervisor-cycle
```

returned one derived `preflight_check` task only in stdout, not in DB.

Risk if FAIL:
- The system is still a queue utility, not an autonomous supervisor stack.

Minimal fix suggested:
- Split cycle into: observe -> decide -> persist derived work -> execute/dispatch -> update state.

### G2 - Planner and Executor separation
Status: FAIL

Evidence:
- No `Planner` or `Executor` class/module exists.
- Events do not contain a `role` field.
- `SupervisorResult` is only `action/reason/derived_tasks`.

Risk if FAIL:
- Responsibility boundaries remain implicit; later multi-agent debugging will be ambiguous.

Minimal fix suggested:
- Add explicit `Planner` and `Executor` roles or at minimum emit `role=planner|executor` in event payload/source.

### G3 - Evidence gates before completion
Status: FAIL

Evidence:
- `scripts/agentos.py:560-585` completes a task without validating acceptance requirements.
- Manual proof: a generic task completed successfully with only `control-plane/README.md` as evidence ref.
- There is no logic enforcing `test`, `commit`, `pr_or_pr_update`, or CI evidence for code tasks.

Risk if FAIL:
- Tasks can be marked successful without the delivery evidence required by the migration plan.

Minimal fix suggested:
- Validate `task.acceptance.required` before `task.completed`; reject completion if evidence is incomplete.

### H1 - kind -> objective routing
Status: PASS

Evidence:
- `control-plane/config/routing_rules.json` includes mappings for:
  - `code_impl`
  - `code_review`
  - `debug_ci`
  - `architecture`
  - `planning`
  - `research`
  - `ops_watchdog`
  - `daily_summary`
  - `heartbeat`
  - `default_chat`
  - `image_request`
  - `video_request`
- `scripts/agentos.py:687-754` loads these rules and builds the `model_router.py` command.

Risk if FAIL:
- No cognitive scheduler behavior.

Minimal fix suggested:
- n/a

### H2 - requestedAgent vs effectiveAgent
Status: PASS

Evidence:
- Requested != effective:

```bash
python3 scripts/agentos.py route --kind code_impl --requested-agent codex --allowed-agents gemini --probe
```

returned:
- `requestedAgent=codex`
- `effectiveAgent=gemini`
- `reason=allowedAgents restricts execution to gemini`

- Requested == effective:

```bash
python3 scripts/agentos.py route --kind planning --requested-agent gemini --allowed-agents gemini
```

returned:
- `requestedAgent=gemini`
- `effectiveAgent=gemini`
- `reason=requested agent allowed`

Risk if FAIL:
- Routing audits would lose intent vs actual execution.

Minimal fix suggested:
- n/a

### I1 - Test plan
Status: PASS

Evidence:
- Tests implemented in `tests/unit/test_agentos.py`:
  - schema validation (`:33-37`)
  - lease/heartbeat/expire/reclaim (`:39-58`)
  - retry exhaustion (`:59-85`)
  - preflight deny (`:86-103`)
  - telegram chunking (`:104-110`)
  - model routing (`:112-125`)
  - supervisor safe-mode guard (`:127-134`)
- Execution:

```bash
python3 -m unittest tests.unit.test_agentos
```

Output summary:
- `Ran 7 tests in 0.865s`
- `OK`

- Broader gate:

```bash
./scripts/test_gate.sh
```

Output summary:
- unit tests: `16 OK`
- regression tests: `6 OK`
- integration tests skipped unless requested

Risk if FAIL:
- Migration regressions would be invisible.

Minimal fix suggested:
- n/a

### I2 - Promotion gate for Green
Status: PASS

Evidence:
- `docs/operations/PROMOTION_ROLLBACK_CHECKLIST.md:19-37` includes:
  - Green health/status checks
  - `./scripts/test_gate.sh --with-integration`
  - soak window requirement
- `docs/operations/BLUE_GREEN_WSL_DOCKER_DESKTOP.md:74-93` documents candidate validation and promotion/rollback steps.

Risk if FAIL:
- Promotion would have no formal release gate.

Minimal fix suggested:
- n/a

### J1 - Safe mode
Status: FAIL

Evidence:
- `control-plane/config/supervisor.json` contains `"safeMode": true`.
- `scripts/agentos.py` exposes `supervisor-cycle --safe-mode`.
- However, `scripts/agentos.py` does not read `control-plane/config/supervisor.json` at runtime for the supervisor path.
- There is no env-based toggle.
- Safe mode is therefore a manual CLI behavior, not an enforced runtime control-plane toggle.

Risk if FAIL:
- Safe-mode cannot be relied on operationally during rollout or incident response.

Minimal fix suggested:
- Load `control-plane/config/supervisor.json` (and optionally env override) inside the supervisor entrypoint.

### J2 - Rollback and artifact preservation
Status: PASS

Evidence:
- `docs/operations/PROMOTION_ROLLBACK_CHECKLIST.md:51-57` documents rollback steps.
- `docs/operations/BLUE_GREEN_WSL_DOCKER_DESKTOP.md:56-93` documents parallel Blue/Green and rollback discipline.
- Agent OS artifacts are persisted locally under:
  - `control-plane/artifacts/events/`
  - `control-plane/artifacts/tasks/`
  - `control-plane/state/agentos.db`

Risk if FAIL:
- Post-mortem evidence would be lost during failed promotions.

Minimal fix suggested:
- n/a

## Top 5 Gaps

1. Supervisor does not enforce preflight or persist derived work.
2. Completion has no acceptance/evidence gate.
3. Retry scheduling has no real backoff state.
4. Telegram envelope lacks summarization/sanitization rules.
5. Control-plane structure is incomplete (`policies/`, `scripts/`, missing `task.handoff`).

## Go / No-Go

Decision: NO-GO for promotion as a full Agent OS migration.

Justification:
- The queue, event log, routing, schema validation, and test scaffolding exist.
- The autonomous control-plane behaviors required by the plan do **not** exist yet in enforceable form.
- In particular, preflight enforcement, supervisor autonomy, evidence gating, and delayed retry semantics are still incomplete.
- Current state is best described as: `Agent OS foundation / scaffolding present, migration not complete`.

## Minimal Correction Plan

- fix 1: complete control-plane layout
  - add `control-plane/policies/`
  - add `control-plane/scripts/` wrappers or extracted entrypoints
  - add `task.handoff`
- fix 2: enforce preflight in supervisor
  - persist preflight tasks or execute preflight inline
  - block sensitive tasks on deny with `task.blocked` and `denyReason`
- fix 3: implement real retry backoff
  - add `next_run_at` to `tasks`
  - exclude future tasks from claim selection until eligible
- fix 4: add acceptance/evidence gating
  - require tests/commit/PR evidence before `task.completed` for code tasks
- fix 5: harden Telegram envelope
  - sanitize large JSON/log payloads
  - convert oversized diagnostics into artifact references
- fix 6: wire safe-mode from config/env
  - runtime config should toggle supervisor behavior without code edits
- re-run checklist:
  - `python3 -m unittest tests.unit.test_agentos`
  - `./scripts/test_gate.sh`
  - preflight allow/deny manual checks
  - supervisor deny-path demo with persisted blocked event
