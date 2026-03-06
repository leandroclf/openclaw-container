# OpenClaw Workspace Architecture (Control Plane)

Updated: 2026-03-05 (America/Sao_Paulo)

## 1) Scope and objective

This document details the architecture of the OpenClaw workspace (`~/clawd`) as an
operations control plane that coordinates:

- agent identity and behavior rules
- multi-agent governance
- kanban and delivery operations
- CI/CD monitoring and alert ownership
- product-repo execution boundaries
- memory continuity and anti-context-loss guardrails

The goal is to support technical reviews, design evolution, and safe scaling
without regressing production automation.

## 2) High-level architecture

```text
Telegram/User
   |
   v
OpenClaw Gateway (container: openclaw)
   |
   +--> Agent runtime (main + subagents via ACP/ACPX)
   |
   +--> Workspace mount: /home/node/clawd  (host: ~/clawd)
            |
            +--> Identity/behavior layer (AGENTS.md, SOUL.md, USER.md, IDENTITY.md)
            +--> Governance layer (ops/multiagent/*)
            +--> Delivery layer (ops/multiagent/delivery/*)
            +--> Product repos (projects/lf-*)
            +--> Skills governance (ops/skills-governance/*)
            +--> Memory layer (memory/*, MEMORY_EXECUTIVE.md)
            +--> Dashboard data sync (dashboards/data/*)
```

## 3) Layered design (workspace)

### L0 - Runtime boundary

- Runtime host path: `~/clawd`
- Container path: `/home/node/clawd`
- This is the workspace state and orchestration plane.
- Infra/runtime hardening remains in `openclaw-container` repo (separate concern).

### L1 - Identity and behavior contracts

Primary files:
- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `IDENTITY.md`
- `MEMORY_EXECUTIVE.md`
- `HEARTBEAT.md`

Responsibilities:
- define persona, scope, communication, and execution rules
- define read order per session
- define autonomy vs escalation boundaries
- enforce transparency format (`Agente`, `Skill`, `Workflow`)

### L2 - Continuity and recovery guardrails

Primary files:
- `ops/multiagent/SESSION_RECOVERY.md`
- `ops/multiagent/MEMORY_GUARDRAILS.md`
- `memory/YYYY-MM-DD.md`
- `.openclaw/workspace-state.json`

Responsibilities:
- prevent context loss after session resets
- prevent recurring auth/repo confusion
- enforce canonical repo mapping and token auth policy
- preserve operational memory deltas per day

### L3 - Multi-agent governance model

Primary files:
- `ops/multiagent/README.md`
- `ops/multiagent/team-categories.md`
- `ops/multiagent/team-capability-matrix.md`
- `ops/multiagent/workflow-skill-routing.md`
- `ops/multiagent/agent-precedence-policy.md`

Responsibilities:
- define specialist taxonomy and capability matrix
- bind workflows to proper specialist + skill sets
- enforce owner/category/KPI metadata in tasks
- define AUTO-first with controlled HUMAN escalation

### L4 - Delivery operations and control

Primary files:
- `ops/multiagent/delivery/board.md`
- `ops/multiagent/delivery/daily-summary.md`
- `ops/multiagent/delivery/ALERT_OWNERSHIP_POLICY.md`
- `ops/multiagent/delivery/repositories.json`
- `ops/multiagent/delivery/deploy-status.json`
- `ops/multiagent/delivery/product-code-progress.json`
- `ops/multiagent/delivery/repo-access-status.md`

Scripts:
- `ops/multiagent/delivery/github_ci_status.py`
- `ops/multiagent/delivery/scripts/repo_access_preflight.py`
- `ops/multiagent/delivery/scripts/product_progress_snapshot.py`
- `ops/multiagent/delivery/scripts/ops_state_lint.py`

Responsibilities:
- run CI/deploy audit and write machine + human readable artifacts
- compute progress snapshots for product repos
- enforce evidence policy for incidents and handoffs
- maintain kanban status and operational semaphore

### L5 - Product execution boundary

Canonical map:
- ISSUE-001 -> `projects/lf-openalex-enrichment-mvp`
- ISSUE-002 -> `projects/lf-wikidata-entity-graph`
- ISSUE-003 -> `projects/lf-worldbank-risk-pricing`

Guardrails:
- `bin/git-safe` enforces HTTPS + token auth and blocks repo mismatch on push/commit
- no product-code commits in workspace root
- no product-code commits in legacy folders (`openalex_enrichment_mvp`, `wikidata_entity_graph`)

### L6 - Skills governance and capability evolution

Primary files:
- `ops/skills-governance/README.md`
- `ops/skills-governance/skill-selection-policy.md`
- `ops/skills-governance/approved-skillset.json`
- `ops/skills-governance/lf-skill-pilot-backlog-2026-02-26.json`
- `ops/skills-governance/lf-skill-routing-map-2026-02-26.md`

Responsibilities:
- control which skills are approved, piloted, or blocked
- tie skill adoption to measurable value and low-risk operations
- prevent uncontrolled expansion of specialist/tool surface area

### L7 - Dashboard and reporting outputs

Primary files:
- `dashboards/data/deploy-status.json`
- `dashboards/data/deploy-status.md`
- `tools/sync_dashboard_data.py`
- `tools/watchdog_monitor.py`

Responsibilities:
- mirror delivery status for dashboard consumers
- detect stagnation/blockers and suggest actions
- maintain a consistent operation-facing view of system health

## 4) Data model and state artifacts

### Core structured states

- `repositories.json`: canonical owner/repo/path and CI provider map
- `deploy-status.json`: CI run snapshot and consecutive failure counters
- `product-code-progress.json`: branch/commit/ahead-behind/worktree/open PR indicators
- `semaphore-state.json`: aggregated operational state
- `autopilot-sla.json`: cycle completion and duration KPIs
- `handoff-master.json`: governance and team metadata

### Mutable narrative states

- `daily-summary.md`: operational timeline
- `board.md`: issue states and priorities
- `memory/*.md`: continuity notes and session context

## 5) Control loops (operational behavior)

### Loop A - CI status audit
1. Read repository map (`repositories.json`)
2. Pull latest workflow runs from GitHub API
3. Compute `consecutiveFailures`
4. Apply ownership policy (`ALERT_OWNERSHIP_POLICY.md`)
5. Persist `deploy-status.json` and update `daily-summary.md`

### Loop B - Product progress snapshot
1. Resolve canonical product repos
2. Fetch remote and inspect local branch state
3. Compute commits in last 48h, ahead/behind, worktree changes, open PR count
4. Persist `product-code-progress.json` and `product-code-progress.md`

### Loop C - Access preflight before blocker claims
1. Validate local dir exists and is git repo
2. Validate authenticated remote access via `bin/git-safe`
3. Persist `repo-access-status.md`
4. Block escalation claims without preflight evidence

### Loop D - Ops consistency lint
1. Validate required files exist
2. Validate required task metadata (`ownerPrimary`, `categoryPrimary`, `valueKpi`)
3. Optionally auto-fix missing metadata
4. Persist lint report

## 6) RACI (execution accountability)

| Domain | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| CI incident 2-4 failures | devops-ci-cd-specialist | reviewer-delivery | infra-analyst | orchestrator |
| CI incident >=5 failures | devops-ci-cd-specialist + infra-analyst | reviewer-delivery + Leandro | architect-tech | team |
| Product implementation | builder-repo / architect-tech | reviewer-delivery | strategist-product | orchestrator |
| Governance model updates | team-evolution-governor | reviewer-delivery | orchestrator | Leandro |
| Skill lifecycle | team-evolution-governor | reviewer-delivery | specialist owners | Leandro |
| Session recovery/auth context | orchestrator | reviewer-delivery | infra-analyst | team |

## 7) Known constraints and technical debt

1) Mixed mutable workspace state
- workspace contains governance artifacts + product repos + local utilities
- risk: noisy git state and accidental cross-domain commits

2) Root board drift
- `board.md` at workspace root contains records of commits to wrong repo path historically
- canonical board is `ops/multiagent/delivery/board.md`

3) Partial dashboard state duplication
- same signals can exist in `ops/multiagent/delivery/*` and `dashboards/data/*`
- requires strict sync ownership to avoid stale dashboards

4) Uneven freshness
- some governance baselines (for example `autopilot-sla.json`) are older than real-time delivery outputs

## 8) Evolution roadmap (workspace only)

### Phase 1 - Canonicalization (low risk)
- enforce single canonical board path and deprecate root duplicates
- add freshness SLA checks for key JSON artifacts
- add daily drift report: stale files, orphan docs, conflicting states

Acceptance:
- zero ambiguity on canonical files
- automated freshness warning in daily summary

### Phase 2 - Reliability hardening
- add deterministic schema validation for `deploy-status.json`, `product-code-progress.json`, `handoff-master.json`
- add idempotent repair routines for known drift patterns
- add policy checks to block invalid escalations (no evidence, wrong severity)

Acceptance:
- no invalid escalation messages in 7-day window
- no broken JSON/schema on critical state files

### Phase 3 - Throughput and governance quality
- optimize specialist allocation from real backlog and repo health
- add objective-based cycle planning with measurable throughput targets
- add auto-close criteria for stale issues with no actionable dependency

Acceptance:
- higher commit throughput in product repos
- lower stale-issue ratio
- lower human intervention count for AUTO-eligible work

## 9) Immediate recommendations for your review deck

1. Present workspace as a control-plane architecture, not just a repo.
2. Show the guardrail stack:
   - session recovery policy
   - canonical repo map
   - git-safe boundary enforcement
   - alert ownership policy
3. Highlight measurable signals:
   - CI consecutive failures
   - product commit velocity (48h window)
   - stale repo detection
4. Propose Phase 1 canonicalization as the next low-risk investment.

## 10) File map (quick reference)

- Identity: `AGENTS.md`, `SOUL.md`, `USER.md`, `IDENTITY.md`
- Recovery: `ops/multiagent/SESSION_RECOVERY.md`, `ops/multiagent/MEMORY_GUARDRAILS.md`
- Governance: `ops/multiagent/team-capability-matrix.md`, `ops/multiagent/workflow-skill-routing.md`
- Delivery: `ops/multiagent/delivery/board.md`, `ops/multiagent/delivery/daily-summary.md`
- CI monitor: `ops/multiagent/delivery/github_ci_status.py`
- Progress monitor: `ops/multiagent/delivery/scripts/product_progress_snapshot.py`
- Access preflight: `ops/multiagent/delivery/scripts/repo_access_preflight.py`
- Repo boundary guard: `bin/git-safe`
- Skills governance: `ops/skills-governance/README.md`
