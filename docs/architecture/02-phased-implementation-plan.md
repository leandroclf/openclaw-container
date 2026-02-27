# Phased Implementation Plan (No Downtime First)

This plan assumes OpenClaw is already running in production and must not be
taken offline by architecture upgrades.

## Global change policy

1. One layer at a time.
2. Apply changes behind feature flags or profile-based compose services.
3. Validate with explicit health checks and runtime smoke tests.
4. Prepare rollback before deployment.
5. If a phase fails validation, rollback immediately and stop progression.

## Baseline before any change

Run and save output snapshots:
- `docker ps --filter name=openclaw`
- `docker exec openclaw openclaw --profile prod gateway health`
- `docker exec openclaw openclaw --profile prod status`
- `tail -n 200 ~/openclaw/logs/openclaw-$(date +%F).log`

Store baseline in `ops/baselines/` with timestamp.

## Phase 0 - Documentation and contracts

Goal:
- Lock architecture boundaries and rollout contracts before code changes.

Changes:
- Add architecture docs and repo boundary docs.
- Define compose profiles (`core`, `obs`, `security`, `eval`).

Validation:
- No runtime changes.
- `git diff` only docs and non-runtime templates.

Rollback:
- Not needed.

## Phase 1 - Observability foundation (read-only impact)

Goal:
- Add visibility first to reduce blind changes later.

Changes:
- Add OTel Collector + Loki + Prometheus + Grafana services.
- Attach log/metric scraping from existing OpenClaw container.

Validation:
- OpenClaw health unchanged.
- Grafana dashboards show container CPU/RAM, gateway latency, error rates.
- No increase in OpenClaw error rate after 24h.

Rollback trigger:
- Host memory pressure causing OpenClaw instability.

Rollback action:
- Stop `obs` profile services only.

## Phase 2 - Async backbone (NATS JetStream)

Goal:
- Introduce resilient async channel for heavy or delayed tasks.

Changes:
- Deploy NATS with persistent volume.
- Start with non-critical jobs only.

Validation:
- JetStream durable stream survives restart.
- No OpenClaw health degradation.
- Retry flows complete after transient provider errors.

Rollback trigger:
- Queue backlog growth without processing recovery.

Rollback action:
- Disable NATS publishers/consumers and return jobs to direct execution.

## Phase 3 - Policy engine (OPA)

Goal:
- Externalize policy decisions with auditability.

Changes:
- Deploy OPA container.
- Start in `audit` mode (decision logged, not enforced).

Validation:
- Policy decisions logged for at least 1 week.
- No false deny events in sampled decisions.

Rollback trigger:
- Policy mismatch with production behavior.

Rollback action:
- Keep OPA online but disable enforcement; fallback to existing behavior.

## Phase 4 - Secrets hardening (Vault)

Goal:
- Move runtime secrets from static env-only patterns to managed retrieval.

Changes:
- Deploy Vault (Raft storage).
- Migrate one non-critical secret path first.

Validation:
- OpenClaw reads migrated secret successfully.
- Renewal/rotation tested in staging profile.

Rollback trigger:
- Authentication or renewal failure.

Rollback action:
- Revert service to known working env var source.

## Phase 5 - Cache and cost controls (Redis Stack)

Goal:
- Reduce repeated model cost and latency.

Changes:
- Add Redis cache for deterministic and semi-deterministic responses.
- Define TTL by objective (short TTL for coding; longer for static research).

Validation:
- Cache hit rate measurable.
- Reduced median latency and token usage on repeated tasks.

Rollback trigger:
- Stale cache causing incorrect operational decisions.

Rollback action:
- Disable cache read path while preserving write metrics for analysis.

## Phase 6 - Execution isolation (gVisor)

Goal:
- Reduce blast radius for risky command execution.

Changes:
- Enable `runsc` for selected worker paths first.

Validation:
- Command compatibility smoke tests pass.
- No critical slowdown for primary workflows.

Rollback trigger:
- Incompatible syscalls or unacceptable latency.

Rollback action:
- Return affected services to default runtime only.

## Phase 7 - Eval gates (Promptfoo)

Goal:
- Add quality regression checks before policy/routing updates.

Changes:
- Add prompt/test suites for coding, reasoning, retrieval, safety.
- Schedule evaluation jobs via Prefect or cron.

Validation:
- Baseline pass thresholds stable for 7 days.
- Routing/policy changes blocked when eval score regresses.

Rollback trigger:
- False failures blocking normal operation.

Rollback action:
- Mark failing suite as non-blocking while root cause is fixed.

## Phase 8 - Full orchestration layer (Prefect)

Goal:
- Standardize background pipelines across all layers.

Changes:
- Introduce Prefect flows incrementally (one flow family at a time).
- Keep existing cron jobs as fallback until each flow proves stable.

Validation:
- Equivalent or better success rate vs previous cron.
- No missed daily critical jobs.

Rollback trigger:
- Any missed critical SLA cycle.

Rollback action:
- Re-enable original cron job immediately.

## Progression gate checklist (required per phase)

- [ ] OpenClaw gateway health remains `ok`.
- [ ] Telegram control channel still responds.
- [ ] No sustained increase in `rate_limit` + timeout combined failure rate.
- [ ] Rollback path tested once before moving forward.
- [ ] Documentation updated in this repo and workspace repo when needed.
