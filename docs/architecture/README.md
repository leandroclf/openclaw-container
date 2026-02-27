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

## Rollout policy

- Do not introduce multiple new core services in a single release wave.
- Validate health, latency, and logs after each phase.
- Keep rollback commands prepared before each deployment.
- Use loopback-only exposure for admin endpoints unless explicitly required.
