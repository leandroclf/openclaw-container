#!/usr/bin/env python3
"""Update autopilot SLA artifacts from workspace telemetry."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


JOB_ID = "25d0fcc7-c72a-4e8f-be0d-0819865a3560"
JOB_NAME = "Autopilot sequential delivery cycle"


def parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def count_human_markers(summary_path: Path, history_dir: Path, window_start: datetime, window_end: datetime) -> int:
    count = 0

    if summary_path.exists():
        count += summary_path.read_text(encoding="utf-8", errors="replace").count("HUMAN_BLOCKER")

    if history_dir.exists():
        for path in sorted(history_dir.glob("*.md")):
            stamp = parse_iso(f"{path.stem}T00:00:00Z")
            if stamp is None:
                continue
            if stamp > window_end or stamp < (window_start - timedelta(days=1)):
                continue
            count += path.read_text(encoding="utf-8", errors="replace").count("HUMAN_BLOCKER")

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--sync-dashboard", action="store_true")
    args = parser.parse_args()

    root = Path(args.workspace_root).expanduser().resolve()
    delivery_dir = root / "ops" / "multiagent" / "delivery"
    cycle_history_path = delivery_dir / "autopilot-cycle-history.json"
    sla_json_path = delivery_dir / "autopilot-sla.json"
    sla_md_path = delivery_dir / "autopilot-sla.md"
    daily_summary_path = delivery_dir / "daily-summary.md"
    history_dir = delivery_dir / "daily-summary-history"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    window_start = now - timedelta(hours=24)

    cycle_history = load_json(cycle_history_path)
    previous = load_json(sla_json_path) if sla_json_path.exists() else {}

    filtered_cycles = []
    for cycle in cycle_history.get("cycles", []):
        started_at = parse_iso(cycle.get("startedAt"))
        ended_at = parse_iso(cycle.get("endedAt"))
        if started_at is None or ended_at is None:
            continue
        if (
            window_start <= started_at <= now
            or window_start <= ended_at <= now
            or (started_at <= window_start and ended_at >= now)
        ):
            filtered_cycles.append(cycle)

    notes: list[str] = []
    if filtered_cycles:
        cycles_run = len(filtered_cycles)
        cycles_completed = sum(1 for cycle in filtered_cycles if cycle.get("status") == "SUCESSO")
        cycles_interrupted = sum(1 for cycle in filtered_cycles if cycle.get("status") == "INTERRUPTED")
        total_duration_ms = sum(int(cycle.get("durationMs", 0) or 0) for cycle in filtered_cycles)
        cycle_completion_pct = round((cycles_completed / cycles_run * 100) if cycles_run else 0, 2)
        avg_cycle_duration_minutes = round((total_duration_ms / cycles_run / 60000) if cycles_run else 0, 2)

        summary_markers = count_human_markers(daily_summary_path, history_dir, window_start, now)
        cycle_history_human = sum(1 for cycle in filtered_cycles if cycle.get("blockerType") == "HUMAN_BLOCKER")
        if summary_markers > 0:
            human_intervention_count = summary_markers
        else:
            human_intervention_count = cycle_history_human
            if cycle_history_human > 0:
                notes.append(
                    "No explicit HUMAN_BLOCKER markers found in daily-summary for the rolling window. "
                    "Using blockerType=HUMAN_BLOCKER from autopilot-cycle-history.json."
                )
    else:
        previous_kpis = previous.get("kpis", {})
        cycles_run = int(previous_kpis.get("cyclesRun", 0) or 0)
        cycles_completed = int(previous_kpis.get("cyclesCompleted", 0) or 0)
        cycles_interrupted = int(previous_kpis.get("cyclesInterrupted", 0) or 0)
        cycle_completion_pct = float(previous_kpis.get("cycleCompletionPct", 0) or 0)
        avg_cycle_duration_minutes = float(previous_kpis.get("avgCycleDurationMinutes", 0) or 0)
        human_intervention_count = int(previous_kpis.get("humanInterventionCount", 0) or 0)
        notes.append(
            "No new cycle data found in autopilot-cycle-history.json for the last 24h rolling window "
            f"({window_start.isoformat().replace('+00:00', 'Z')} to {now.isoformat().replace('+00:00', 'Z')}). "
            "Using previous valid KPI values."
        )

    payload = {
        "updatedAt": now.isoformat().replace("+00:00", "Z"),
        "window": {
            "kind": "rolling-24h",
            "start": window_start.isoformat().replace("+00:00", "Z"),
            "end": now.isoformat().replace("+00:00", "Z"),
        },
        "job": {
            "name": JOB_NAME,
            "id": JOB_ID,
        },
        "kpis": {
            "cycleCompletionPct": cycle_completion_pct,
            "avgCycleDurationMinutes": avg_cycle_duration_minutes,
            "cyclesRun": cycles_run,
            "cyclesCompleted": cycles_completed,
            "cyclesInterrupted": cycles_interrupted,
            "humanInterventionCount": human_intervention_count,
        },
        "telemetry": {
            "source": "ops/multiagent/delivery/autopilot-cycle-history.json",
            "fields": ["cycleId", "startedAt", "endedAt", "durationMs", "status", "blockerType"],
        },
        "notes": notes,
    }

    lines = [
        "# Autopilot Sequential Delivery Cycle SLA (Rolling 24h)",
        "",
        f"**Job ID:** `{JOB_ID}`",
        f"**Job Name:** {JOB_NAME}",
        f"**Última Atualização:** {payload['updatedAt']}",
        f"**Período (Rolling 24h):** {payload['window']['start']} to {payload['window']['end']}",
        "",
        "## KPIs de Desempenho",
        "",
        f"*   **Ciclos Executados (cyclesRun):** {cycles_run}",
        f"*   **Ciclos Completados (cyclesCompleted):** {cycles_completed}",
        f"*   **Ciclos Interrompidos (cyclesInterrupted):** {cycles_interrupted}",
        f"*   **Percentual de Conclusão de Ciclos (cycleCompletionPct):** {cycle_completion_pct:.2f}%",
        f"*   **Duração Média do Ciclo (avgCycleDurationMinutes):** {avg_cycle_duration_minutes:.2f} minutos",
        f"*   **Contagem de Intervenções Humanas (humanInterventionCount):** {human_intervention_count}",
        "",
        "## Notas",
        "",
    ]
    lines.extend([f"*   {note}" for note in notes] or ["*   Nenhuma."])
    lines.extend(
        [
            "",
            "---",
            "**Transparência Operacional:**",
            "*   **Agente:** operations-analytics-specialist",
            "*   **Skill:** n/a (execução direta determinística)",
            "*   **Workflow:** Daily autopilot SLA tracker",
        ]
    )

    sla_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sla_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.sync_dashboard:
        dashboard_sync = root / "tools" / "sync_dashboard_data.py"
        if dashboard_sync.exists():
            import subprocess

            subprocess.run(["python3", str(dashboard_sync)], cwd=str(root), check=True)

    print(f"autopilot_sla_json={sla_json_path}")
    print(f"autopilot_sla_md={sla_md_path}")


if __name__ == "__main__":
    main()
