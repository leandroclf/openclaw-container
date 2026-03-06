# OpenClaw Integration Architecture (Phased)

This folder documents the target integration architecture to evolve OpenClaw
without service regression.

Primary constraint:
- OpenClaw in production must remain online during rollout.
- Every change is phased, reversible, and validated before promotion.

## Documents

1. `01-target-architecture.md`
   - Functional layers, selected technology per layer, and rationale.
2. `02-phased-implementation-plan.md`
   - Incremental rollout plan with checkpoints and go/no-go gates.
3. `03-risk-register-and-rollback.md`
   - Technical/operational risks and rollback playbooks.
4. `04-repo-boundaries-and-versioning.md`
   - Clear split between infra repo and workspace repo.
5. `05-docker-topology.md`
   - Internal container communication, networks, volumes, and secrets flow.
6. `06-openclaw-workspace-control-plane.md`
   - Full workspace architecture (control plane), governance loops, RACI, risks, and roadmap.
7. `OpenClaw_AgentOS_Migration.md`
   - Executable migration plan toward an Agent OS architecture.
8. `08-agentos-audit-report-2026-03-05.md`
   - Initial PASS/FAIL audit of the Agent OS migration before remediation.
9. `09-agentos-remediation-validation-2026-03-05.md`
   - Post-fix validation of the Agent OS control-plane foundation.

## Rollout policy

- Do not introduce multiple new core services in a single release wave.
- Validate health, latency, and logs after each phase.
- Keep rollback commands prepared before each deployment.
- Use loopback-only exposure for admin endpoints unless explicitly required.
