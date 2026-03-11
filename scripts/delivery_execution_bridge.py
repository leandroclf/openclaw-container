#!/usr/bin/env python3
"""Build and optionally activate a delivery execution intent from a ready handoff."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

FRESHNESS_LIMIT = timedelta(minutes=45)
ROOT_DIR = Path(__file__).resolve().parents[1]
DELIVERY_TEMPLATE_PATH = ROOT_DIR / "control-plane" / "config" / "delivery_executor_message.txt"


def parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_json(cmd: list[str]) -> object:
    return json.loads(subprocess.check_output(cmd, text=True))


def run_text(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def build_agent_message(request: dict) -> str:
    template = DELIVERY_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    task = request.get("task", {})
    handoff_json = json.dumps(request, ensure_ascii=False, indent=2)
    return (
        f"{template}\n\n"
        "HANDOFF ATUAL:\n"
        f"- requestId: {request.get('requestId')}\n"
        f"- issueId: {task.get('issueId')}\n"
        f"- repo: {task.get('repo')}\n"
        f"- branch: {task.get('branch')}\n"
        f"- kind: {task.get('kind')}\n"
        f"- workflow: {task.get('workflow')}\n\n"
        "IMPORTANTE:\n"
        "- Se o arquivo de handoff fora do workspace nao puder ser lido diretamente, use o JSON embutido abaixo como fonte oficial.\n"
        "- Nao bloqueie por falta de acesso ao arquivo de handoff se o JSON abaixo estiver presente.\n\n"
        "JSON DO HANDOFF:\n"
        "```json\n"
        f"{handoff_json}\n"
        "```\n\n"
        "CONTRATO DE RESPOSTA OBRIGATÓRIO:\n"
        "1. Tente escrever `/home/node/.openclaw/agentos/handoffs/delivery-execution-result.json`.\n"
        "2. Na resposta final, inclua exatamente um bloco com o marcador `DELIVERY_RESULT_JSON` seguido por JSON válido com:\n"
        "   - requestId\n"
        "   - issueId\n"
        "   - status (`succeeded|blocked|failed`)\n"
        "   - repo\n"
        "   - branch\n"
        "   - tests[]\n"
        "   - commit\n"
        "   - pr\n"
        "   - ciStatus (`pass|fail|unknown`)\n"
        "   - blockerType\n"
        "   - blockerReason\n"
        "   - updatedAt\n"
        "3. Se não houver progresso técnico real, retorne `status=blocked` com causa raiz objetiva.\n"
        "4. Não inclua nenhum outro JSON na resposta final."
    )


def extract_result_from_payloads(payloads: list[dict]) -> dict | None:
    texts = [payload.get("text", "") for payload in payloads if payload.get("text")]
    joined = "\n".join(texts)
    patterns = [
        r"DELIVERY_RESULT_JSON\s*```json\s*(\{.*?\})\s*```",
        r"DELIVERY_RESULT_JSON\s*(\{.*\})",
    ]
    for pattern in patterns:
        match = re.search(pattern, joined, flags=re.DOTALL)
        if not match:
            continue
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    for text in texts:
        stripped = text.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def build_blocked_result(request: dict, reason: str, blocker_type: str = "SOFT_BLOCKER") -> dict:
    task = request.get("task", {})
    return {
        "requestId": request.get("requestId"),
        "issueId": task.get("issueId"),
        "status": "blocked",
        "repo": task.get("repo"),
        "branch": task.get("branch"),
        "tests": [],
        "commit": None,
        "pr": None,
        "ciStatus": "unknown",
        "blockerType": blocker_type,
        "blockerReason": reason,
        "updatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def resolve_cron_job(profile: str, cron_name: str) -> dict | None:
    payload = run_json(["docker", "exec", "openclaw", "openclaw", "--profile", profile, "cron", "list", "--json"])
    jobs = payload["jobs"] if isinstance(payload, dict) else payload
    for job in jobs:
        if job.get("name") == cron_name:
            return job
    return None


def render_md(intent: dict) -> str:
    lines = [
        "# Delivery Execution Intent",
        "",
        f"requestId: `{intent['requestId']}`",
        f"generatedAt: `{intent['generatedAt']}`",
        f"mode: `{intent['mode']}`",
        f"status: `{intent['status']}`",
        "",
        "## Guards",
        f"- internalDeliveryPrimary: `{intent['guards']['internalDeliveryPrimary']}`",
        f"- consumerReady: `{intent['guards']['consumerReady']}`",
        f"- requestFresh: `{intent['guards']['requestFresh']}`",
        f"- duplicateExecutionPrevented: `{intent['guards']['duplicateExecutionPrevented']}`",
        f"- targetCronEnabled: `{intent['guards']['targetCronEnabled']}`",
        f"- targetCronRunning: `{intent['guards']['targetCronRunning']}`",
        "",
        "## Source Task",
        f"- issueId: `{intent['source']['issueId']}`",
        f"- taskId: `{intent['source']['taskId']}`",
        f"- repo: `{intent['source']['repo']}`",
        f"- branch: `{intent['source']['branch']}`",
        f"- kind: `{intent['source']['kind']}`",
        "",
        "## Execution",
        f"- triggerMethod: {intent['execution'].get('triggerMethod', 'not configured')}",
        f"- sideEffect: {intent['execution'].get('sideEffect', 'none in dry-run mode')}",
    ]
    if intent["execution"].get("jobId"):
        lines.append(f"- cronJobId: `{intent['execution']['jobId']}`")
    if intent["execution"].get("result"):
        lines.append(f"- triggerResult: `{intent['execution']['result']}`")
    if intent.get("notes"):
        lines.extend(["", "## Notes"])
        lines.extend(f"- {note}" for note in intent["notes"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--profile", default="prod")
    parser.add_argument("--backend", choices=["agent", "cron"], default="agent")
    parser.add_argument("--trigger-agent", default="main")
    parser.add_argument("--agent-timeout-seconds", default="1800")
    parser.add_argument("--trigger-cron-name", default="Autopilot sequential delivery cycle")
    parser.add_argument("--trigger-cron-id", default=None)
    parser.add_argument("--trigger-timeout-ms", default="900000")
    parser.add_argument(
        "--internal-delivery-primary",
        choices=["true", "false"],
        default="true",
        help="Keep true while the internal delivery cron remains the primary scheduler.",
    )
    parser.add_argument(
        "--allow-disabled-cron",
        action="store_true",
        help="Allow activation even if the target cron is disabled, as long as it still resolves by name.",
    )
    args = parser.parse_args()

    bridge_dir = Path(args.bridge_dir).expanduser().resolve()
    request_path = bridge_dir / "delivery-execution-request.json"
    consumer_state_path = bridge_dir / "delivery-handoff-state.json"
    execution_state_path = bridge_dir / "delivery-execution-state.json"
    intent_json_path = bridge_dir / "delivery-execution-intent.json"
    intent_md_path = bridge_dir / "delivery-execution-intent.md"
    agent_output_path = bridge_dir / "delivery-execution-agent-output.json"
    result_path = bridge_dir / "delivery-execution-result.json"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    internal_primary = args.internal_delivery_primary == "true"

    if not request_path.exists():
        print("[DELIVERY_EXECUTION_NO_REQUEST]")
        return
    if not consumer_state_path.exists():
        print("[DELIVERY_EXECUTION_BLOCKED] consumer state missing")
        return

    request = load_json(request_path)
    consumer_state = load_json(consumer_state_path)
    execution_state = load_json(execution_state_path) if execution_state_path.exists() else {
        "updatedAt": None,
        "lastPreparedRequestId": None,
        "lastExecutedRequestId": None,
        "status": "empty",
        "notes": [],
    }

    request_id = request.get("requestId")
    created_at = parse_timestamp(request.get("createdAt"))
    request_fresh = created_at is not None and (now - created_at) <= FRESHNESS_LIMIT
    consumer_ready = consumer_state.get("status") == "ready"
    duplicate_prevented = execution_state.get("lastExecutedRequestId") != request_id

    target_job = None
    target_enabled = False
    target_running = False
    target_job_id = None
    if args.backend == "cron":
        target_job = resolve_cron_job(args.profile, args.trigger_cron_name)
        target_enabled = bool(target_job.get("enabled", False)) if target_job else False
        target_running = bool(target_job and target_job.get("state", {}).get("runningAtMs"))
        target_job_id = args.trigger_cron_id or (target_job.get("id") if target_job else None)

    notes: list[str] = []
    if internal_primary:
        notes.append("Internal delivery cron is still the primary scheduler.")
    if not consumer_ready:
        notes.append("Delivery consumer state is not ready.")
    if not request_fresh:
        notes.append("Delivery request is stale.")
    if not duplicate_prevented:
        notes.append("Request was already executed previously.")
    if args.backend == "cron":
        if not target_job_id:
            notes.append(f"Target cron job not found: {args.trigger_cron_name}")
        elif not target_enabled and not args.allow_disabled_cron:
            notes.append("Target cron job is disabled.")
        if target_running:
            notes.append("Target cron job is already running.")

    trigger_method = "none"
    side_effect = "none in dry-run mode"
    trigger_result = None
    trigger_output = None
    if args.activate and not notes:
        try:
            if args.backend == "agent":
                trigger_method = f"openclaw agent --agent {args.trigger_agent}"
                side_effect = "run host-approved direct delivery executor turn"
                trigger_output = run_text(
                    [
                        "docker",
                        "exec",
                        "openclaw",
                        "openclaw",
                        "--profile",
                        args.profile,
                        "agent",
                        "--agent",
                        args.trigger_agent,
                        "--message",
                        build_agent_message(request),
                        "--json",
                        "--timeout",
                        args.agent_timeout_seconds,
                    ]
                )
                parsed_output = json.loads(trigger_output)
                save_json(agent_output_path, parsed_output)
                if not result_path.exists():
                    fallback_result = extract_result_from_payloads(parsed_output.get("result", {}).get("payloads", []))
                    if fallback_result is None:
                        fallback_result = {
                            "requestId": request_id,
                            "issueId": request["task"].get("issueId"),
                            "status": "blocked",
                            "repo": request["task"].get("repo"),
                            "branch": request["task"].get("branch"),
                            "tests": [],
                            "commit": None,
                            "pr": None,
                            "ciStatus": "unknown",
                            "blockerType": "SOFT_BLOCKER",
                            "blockerReason": "agent_result_missing_canonical_output",
                            "updatedAt": now.isoformat().replace("+00:00", "Z"),
                        }
                    save_json(result_path, fallback_result)
            else:
                trigger_method = f"openclaw cron run {args.trigger_cron_name}"
                side_effect = "trigger host-approved internal sequential delivery cycle"
                trigger_output = run_text(
                    [
                        "docker",
                        "exec",
                        "openclaw",
                        "openclaw",
                        "--profile",
                        args.profile,
                        "cron",
                        "run",
                        target_job_id,
                        "--timeout",
                        args.trigger_timeout_ms,
                    ]
                )
            trigger_result = "triggered"
        except subprocess.CalledProcessError as exc:
            trigger_output = (exc.output or "").strip()
            trigger_result = "failed"
            notes.append("Delivery execution activation failed.")
        except json.JSONDecodeError:
            trigger_result = "failed"
            notes.append("Agent execution returned non-JSON output.")
    elif args.activate and notes and not result_path.exists():
        save_json(result_path, build_blocked_result(request, "; ".join(notes)))

    final_notes = notes
    if not notes:
        if args.activate and trigger_result == "triggered":
            if args.backend == "agent":
                final_notes = ["Delivery execution bridge activated and the direct agent executor was triggered."]
            else:
                final_notes = ["Delivery execution bridge activated and the internal sequential delivery cycle was triggered."]
        elif args.activate:
            final_notes = ["Delivery execution bridge activation completed."]
        else:
            final_notes = ["Delivery execution bridge is ready for future ownership transfer."]

    intent = {
        "requestId": request_id,
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "mode": "activate" if args.activate else "dry-run",
        "status": "blocked" if notes else ("activated" if args.activate else "ready"),
        "guards": {
            "internalDeliveryPrimary": internal_primary,
            "consumerReady": consumer_ready,
            "requestFresh": request_fresh,
            "duplicateExecutionPrevented": duplicate_prevented,
            "targetCronEnabled": target_enabled,
            "targetCronRunning": target_running,
        },
        "source": {
            "taskId": request["task"].get("taskId"),
            "issueId": request["task"].get("issueId"),
            "repo": request["task"].get("repo"),
            "branch": request["task"].get("branch"),
            "kind": request["task"].get("kind"),
        },
        "execution": {
            "backend": args.backend,
            "triggerMethod": trigger_method,
            "sideEffect": side_effect,
            "jobId": target_job_id,
            "result": trigger_result,
            "output": trigger_output,
        },
        "notes": final_notes,
    }

    execution_state.update(
        {
            "updatedAt": now.isoformat().replace("+00:00", "Z"),
            "lastPreparedRequestId": request_id,
            "status": intent["status"],
            "notes": intent["notes"],
        }
    )
    if args.activate and not notes:
        execution_state["lastExecutedRequestId"] = request_id
        execution_state["lastTriggerCronJobId"] = target_job_id
        execution_state["lastTriggerResult"] = trigger_result

    save_json(intent_json_path, intent)
    intent_md_path.write_text(render_md(intent), encoding="utf-8")
    save_json(execution_state_path, execution_state)

    if notes:
        print(f"[DELIVERY_EXECUTION_BLOCKED] requestId={request_id}")
    elif args.activate:
        print(f"[DELIVERY_EXECUTION_ACTIVATED] requestId={request_id}")
    else:
        print(f"[DELIVERY_EXECUTION_READY] requestId={request_id}")
    print(f"intent_json={intent_json_path}")
    print(f"intent_md={intent_md_path}")


if __name__ == "__main__":
    main()
