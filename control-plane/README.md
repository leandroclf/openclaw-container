# Agent OS Control Plane

This directory contains the local control-plane assets for the OpenClaw Agent OS
MVP described in `docs/architecture/OpenClaw_AgentOS_Migration.md`.

Contents:

- `schemas/`
  - Canonical JSON schemas for tasks, events, and preflight results.
- `config/`
  - Routing rules and safe-mode defaults for the cognitive scheduler.
  - Workflow registry for low-risk operational flows.
- `policies/`
  - Executable production/preflight policy derived from change-management docs.
- `scripts/`
  - Thin wrappers for schema validation, DB init, preflight, and supervisor cycles.
  - Includes `run_workflow.sh` for low-risk workflow execution via Agent OS.
- `state/`
  - Local SQLite queue state (`agentos.db`) created at runtime.
- `artifacts/`
  - Append-only event logs, task snapshots, evidence references, and reports.

Operational notes:

- The SQLite database is intentionally not committed.
- This control plane is additive and does not change production behavior until
  explicitly wired into existing crons/workflows.
- `scripts/agentos.py` is the executable entrypoint for queue, events,
  scheduler, preflight, and envelope helpers.
