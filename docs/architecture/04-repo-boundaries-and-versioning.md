# Repository Boundaries and Versioning Strategy

This project uses two repositories by design. Keeping boundaries strict is
required for low coupling and safe operations.

## Repository responsibilities

## 1) Infrastructure repo (`openclaw-container`)

Owns:
- Docker image and runtime hardening.
- Compose topology, networks, volumes, dependencies.
- Service-level configs for NATS, OPA, Vault, Redis, Prefect, observability.
- Deployment scripts, backup/restore scripts, host runbooks.

Must not own:
- Workspace behavior content (skills, issue board state, agent memory content).
- Business logic prompts and day-to-day workspace decisions.

## 2) Workspace repo (`openclaw-workspace` / mounted `~/clawd`)

Owns:
- Agent behavior, skills, policies, memory assets, issue workflows.
- Prompt/eval suites tied to operational objectives.
- Daily operational artifacts (summary, handoff, governance docs).

Must not own:
- Container topology, host-level service config, Docker hardening settings.
- Infrastructure secrets or runtime bootstrap scripts.

## Integration contract between repos

- Infra mounts workspace as a volume only:
  - host `~/clawd` -> container `/home/node/clawd`
- Infra can validate workspace schema/contracts but cannot rewrite business docs.
- Workspace can request infra capabilities via documented interface files, not by
  editing infra deployment files directly.

## Versioning model

- Infra repo: semantic tags per deployment wave (`infra-vX.Y.Z`).
- Workspace repo: operational cadence commits (`workspace-YYYYMMDD-<topic>`).
- Link both through release notes:
  - infra release notes include compatible workspace commit range.

## Change control

Any change touching both repos must include:
1. Interface contract update in both repos.
2. Backward compatibility note.
3. Rollback procedure reference.

## Required docs to keep updated

In `openclaw-container`:
- `RUNBOOK.md`
- `docs/architecture/*`
- script usage and compose profile docs

In `openclaw-workspace`:
- policy docs
- skill docs
- operational governance docs
- eval baselines and thresholds
