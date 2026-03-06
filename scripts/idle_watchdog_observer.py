#!/usr/bin/env python3
"""Deterministic host-side observer for the idle watchdog JSON output."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def render_md(report: dict, source_path: str) -> str:
    monitored = report.get("monitored_tasks", [])
    blockers = report.get("blockers", [])
    health = report.get("subagent_health_check", {})

    lines = [
        "# Idle Watchdog Observation",
        "",
        f"Atualizado em: `{report.get('timestamp', 'n/a')}`",
        f"Fonte: `{source_path}`",
        "",
        "## Estado Geral",
        f"- productive_advancement_detected: `{report.get('productive_advancement_detected')}`",
        f"- active_blockers_detected: `{report.get('active_blockers_detected')}`",
        f"- suggested_action: `{report.get('suggested_action', 'n/a')}`",
        f"- reason: {report.get('reason', 'n/a')}",
        f"- eligible_auto_tasks: `{report.get('eligible_auto_tasks', 0)}`",
        "",
        "## Subagent Health",
        f"- actual_count: `{health.get('actual_count', 'n/a')}`",
        f"- consistency_check: `{health.get('consistency_check', 'n/a')}`",
        "",
        "## Blockers",
    ]
    lines.extend([f"- `{item.get('source', 'n/a')}` -> {item.get('details', 'n/a')}" for item in blockers] or ["- nenhum"])
    lines.extend(["", "## Monitored Tasks"])

    if monitored:
        lines.append("| Task | Repo | Latest commit | Advancement |")
        lines.append("|---|---|---|---|")
        for task in monitored:
            lines.append(
                "| {task} | `{repo}` | `{commit}` | `{adv}` |".format(
                    task=task.get("id", task.get("title", "n/a")),
                    repo=task.get("repo_path", "n/a"),
                    commit=task.get("latest_commit_time", "n/a"),
                    adv=task.get("advancement_detected", False),
                )
            )
    else:
        lines.append("- nenhuma")

    lines.extend(
        [
            "",
            "Agente: reviewer-delivery + orchestrator",
            "Skill: n/a (execução direta determinística)",
            "Workflow: idle-watchdog-observer",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument(
        "--output-json",
        default="ops/multiagent/delivery/watchdog-monitor.json",
    )
    parser.add_argument(
        "--output-md",
        default="ops/multiagent/delivery/watchdog-monitor.md",
    )
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).expanduser().resolve()
    output_json = workspace_root / args.output_json
    output_md = workspace_root / args.output_md

    result = subprocess.run(
        ["python3", "tools/watchdog_monitor.py"],
        cwd=str(workspace_root),
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    report["observedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_md(report, "tools/watchdog_monitor.py"), encoding="utf-8")

    print(f"watchdog_json={output_json}")
    print(f"watchdog_md={output_md}")


if __name__ == "__main__":
    main()
