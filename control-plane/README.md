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
  - Includes `weekly_blocker_capture_workflow.py` for the weekly finance/legal capture flow.
  - Includes `finance_export_autowire.py` for finance-export discovery, drop-in wiring, and capture publication when a real export appears.
  - Includes `finance_export_discovery.py` for local source suggestions when the canonical export is missing; the default search now covers common workspaces and Windows user profile roots, and it can still be extended with `OPENCLAW_LEDGER_EXPORT_SEARCH_PATHS` or widened with `OPENCLAW_LEDGER_EXPORT_MAX_DEPTH`.
  - Includes `ledger_export_watchdog.py` for ledger export presence/change alerts.
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
- `tools/weekly_blocker_capture_workflow.py` is the weekly finance/legal capture wrapper that commits and pushes the dated snapshots.
- `scripts/finance_export_autowire.py` is the auto-wiring workflow that discovers a real finance export, connects the canonical drop-in, and republishes the weekly capture when a source is found.
- `scripts/ledger_export_watchdog.py` is the ledger export presence watchdog that alerts when the canonical finance export appears, changes, or disappears.
- `scripts/finance_export_discovery.py` is the helper that suggests likely local export sources so the team can wire the canonical drop-in path faster.
- `scripts/install_finance_export_dropin.sh` is the drop-in installer for wiring a real export into the canonical finance path.
- `scripts/before_agent_reply.py` is the outbound guardrail hook for
  Telegram/Slack/Discord/WhatsApp formatting and approval messages.
