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
  - Includes `agentos.py intake` to normalize channel JSON into the canonical task packet.
  - Includes `channel_intake_bridge.py` for webhook/channel adapters that need the same intake path.
  - Includes `telegram_channel_bridge.py` for polling Telegram channel logs into the same intake path.
  - Includes `run_workflow.sh` for low-risk workflow execution via Agent OS.
- `state/`
  - Local SQLite queue state (`agentos.db`) created at runtime.
- `artifacts/`
  - Append-only event logs, task snapshots, evidence references, and reports.

Operational notes:

- The SQLite database is intentionally not committed.
- This control plane is additive and does not change production behavior until
  explicitly wired into existing crons/workflows.
- `scripts/agentos.py` is the executable entrypoint for queue, events, intake,
  scheduler, preflight, and envelope helpers.
- `scripts/channel_intake_bridge.py` is the adapter entrypoint for external
  channel/webhook payloads that should be normalized into the same packet.
- `scripts/telegram_channel_bridge.py` is the Telegram polling bridge that
  mirrors channel activity into the canonical intake path and keeps the
  omnichannel source contract intact.
