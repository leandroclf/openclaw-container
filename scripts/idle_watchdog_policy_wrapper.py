#!/usr/bin/env python3
"""Apply policy to host-side idle watchdog observation artifacts only."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


FRESHNESS_LIMIT = timedelta(minutes=30)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).expanduser().resolve()
    delivery_dir = workspace_root / "ops" / "multiagent" / "delivery"
    watchdog_json = delivery_dir / "watchdog-monitor.json"
    watchdog_md = delivery_dir / "watchdog-monitor.md"
    daily_summary = delivery_dir / "daily-summary.md"

    now = datetime.now(timezone.utc).replace(microsecond=0)

    report = load_json(watchdog_json)
    observed_at = parse_timestamp(report.get("observedAt") or report.get("timestamp"))
    freshness_ok = observed_at is not None and (now - observed_at) <= FRESHNESS_LIMIT
    age_minutes = round((now - observed_at).total_seconds() / 60, 1) if observed_at else None

    if not freshness_ok:
        lines = [
            f"## Daily Summary - {now.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "### Idle Watchdog Policy",
            "- **Collection Freshness:** STALE.",
            f"- **Source:** `{watchdog_json}`",
            f"- **Observed At:** `{observed_at.isoformat().replace('+00:00', 'Z') if observed_at else 'n/a'}`",
            f"- **Age Minutes:** `{age_minutes if age_minutes is not None else 'n/a'}`",
            "- **Decision:** `HARD_BLOCKER`",
            "- **Next Action:** Regenerar `watchdog-monitor.json` antes de qualquer decisão de handoff.",
            "",
            "### Meta-Information",
            "- **Agent:** reviewer-delivery + orchestrator",
            "- **Skill:** n/a (policy wrapper determinístico)",
            "- **Workflow:** idle-watchdog-policy-wrapper",
        ]
        with daily_summary.open("a", encoding="utf-8") as handle:
            handle.write("\n" + "\n".join(lines) + "\n")
        print("[HARD_BLOCKER] watchdog observation is stale")
        return

    suggested_action = report.get("suggested_action", "NO_ACTION")
    if report.get("active_blockers_detected"):
        decision = "REPORT_BLOCKERS"
        next_action = "Registrar bloqueios e preservar o handoff de execução dentro do OpenClaw interno."
    elif suggested_action == "TRIGGER_MINI_CYCLE":
        decision = "REQUEST_MINI_CYCLE_HANDOFF"
        next_action = "Registrar o pedido de handoff; nao disparar mini-cycle pelo host-side nesta fase."
    else:
        decision = "MONITOR"
        next_action = "Somente monitorar; nenhuma acao host-side adicional."

    blockers = report.get("blockers", [])
    monitored = report.get("monitored_tasks", [])
    lines = [
        f"## Daily Summary - {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "### Idle Watchdog Policy",
        "- **Collection Freshness:** OK.",
        f"- **Source JSON:** `{watchdog_json}`",
        f"- **Source Markdown:** `{watchdog_md}`",
        f"- **Observed At:** `{observed_at.isoformat().replace('+00:00', 'Z')}`",
        f"- **Age Minutes:** `{age_minutes}`",
        f"- **Decision:** `{decision}`",
        f"- **Suggested Action (source):** `{suggested_action}`",
        f"- **Next Action:** {next_action}",
        f"- **Eligible AUTO Tasks:** `{report.get('eligible_auto_tasks', 0)}`",
        f"- **Active Blockers Detected:** `{report.get('active_blockers_detected', False)}`",
        f"- **Productive Advancement Detected:** `{report.get('productive_advancement_detected', False)}`",
    ]

    if blockers:
        lines.append("- **Blockers:** " + "; ".join(str(item) for item in blockers[:3]))
    if monitored:
        tracked = ", ".join(f"`{item.get('id', item.get('title', 'n/a'))}`" for item in monitored[:6])
        lines.append(f"- **Tracked Tasks:** {tracked}")

    lines.extend(
        [
            "",
            "### Meta-Information",
            "- **Agent:** reviewer-delivery + orchestrator",
            "- **Skill:** n/a (policy wrapper determinístico)",
            "- **Workflow:** idle-watchdog-policy-wrapper",
        ]
    )

    with daily_summary.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")

    if decision == "REPORT_BLOCKERS":
        print("[WATCHDOG_REPORT_BLOCKERS]")
    elif decision == "REQUEST_MINI_CYCLE_HANDOFF":
        print("[WATCHDOG_REQUEST_HANDOFF]")
    else:
        print("HEARTBEAT_OK")


if __name__ == "__main__":
    main()
