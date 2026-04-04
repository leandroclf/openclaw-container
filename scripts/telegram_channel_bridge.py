#!/usr/bin/env python3
"""Poll Telegram channel logs and forward inbound updates into Agent OS intake."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import agentos


DEFAULT_CONTAINER = "openclaw"
DEFAULT_PROFILE = "prod"
DEFAULT_LIMIT = 200
DEFAULT_STATE_FILE = Path.home() / "openclaw" / "runtime" / "agentos" / "telegram-channel-bridge-cursor.json"

OUTBOUND_SKIP_MARKERS = (
    "sendmessage ok",
    "telegram message failed",
    "polling stall detected",
    "polling runner stopped",
    "starting provider",
    "restarting",
)
INBOUND_HINTS = (
    "received",
    "incoming",
    "update_id",
    "callback_query",
    "message_id",
    "text=",
    "caption=",
)


def load_snapshot(path: str | None, *, container: str, profile: str, limit: int) -> dict[str, Any]:
    if path:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        command = [
            "docker",
            "exec",
            container,
            "openclaw",
            "--profile",
            profile,
            "channels",
            "logs",
            "--channel",
            "telegram",
            "--json",
            "--lines",
            str(limit),
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            if "No such container" in completed.stderr or "Cannot connect to the Docker daemon" in completed.stderr:
                return {"status": "skipped", "reason": "container_unavailable", "lines": []}
            raise RuntimeError(completed.stderr.strip() or "failed to read telegram channel logs")
        payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("telegram channel snapshot must be a JSON object")
    payload.setdefault("lines", [])
    if not isinstance(payload["lines"], list):
        raise ValueError("telegram channel snapshot must expose a list of lines")
    return payload


def line_digest(line: dict[str, Any]) -> str:
    basis = json.dumps(
        {
            "time": line.get("time"),
            "level": line.get("level"),
            "message": line.get("message"),
            "raw": line.get("raw"),
        },
        sort_keys=True,
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def load_cursor(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    last_time = payload.get("lastTime")
    last_digest = payload.get("lastDigest")
    if not isinstance(last_time, str) or not isinstance(last_digest, str):
        return {}
    return {"lastTime": last_time, "lastDigest": last_digest}


def save_cursor(path: Path, *, last_time: str, last_digest: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"lastTime": last_time, "lastDigest": last_digest}, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def split_new_lines(lines: list[dict[str, Any]], cursor: dict[str, str]) -> list[dict[str, Any]]:
    if not cursor:
        return lines
    last_time = cursor.get("lastTime", "")
    last_digest = cursor.get("lastDigest", "")
    seen_cursor = False
    new_lines: list[dict[str, Any]] = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        current_time = str(line.get("time") or "")
        current_digest = line_digest(line)
        if not seen_cursor:
            if current_time == last_time and current_digest == last_digest:
                seen_cursor = True
            continue
        new_lines.append(line)
    if seen_cursor:
        return new_lines
    return [line for line in lines if isinstance(line, dict) and str(line.get("time") or "") > last_time]


def _regex_value(pattern: str, text: str) -> str | None:
    import re

    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        return None
    value = next((group for group in match.groups() if group is not None), None)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def build_intake_payload_from_log(line: dict[str, Any]) -> dict[str, Any] | None:
    message = str(line.get("message") or "")
    raw = str(line.get("raw") or "")
    combined = f"{message}\n{raw}".strip()
    if not combined:
        return None

    lowered = combined.lower()
    if any(marker in lowered for marker in OUTBOUND_SKIP_MARKERS):
        return None
    if not any(marker in lowered for marker in INBOUND_HINTS):
        return None

    chat = _regex_value(r"\bchat=([^\s]+)", combined)
    update_id = _regex_value(r"\b(?:update_id|updateId)=([^\s]+)", combined)
    callback_id = _regex_value(r"\b(?:callback_query_id|callbackQueryId|callback_id|callbackId)=([^\s]+)", combined)
    message_id = _regex_value(r"\b(?:message_id|messageId|message)=([^\s]+)", combined)
    user_id = _regex_value(r"\b(?:user_id|userId|from)=([^\s]+)", combined)
    text = _regex_value(r"\b(?:text|caption)=(.*)$", combined)

    if text is None and "received" in lowered:
        text = message.strip() or combined.strip()
    if text is None:
        text = message.strip() or combined.strip()

    if not any([chat, update_id, callback_id, message_id, text]):
        return None

    session_key = f"telegram:chat:{chat}" if chat else "telegram:polling"
    if update_id:
        message_ref = f"tg:update:{update_id}"
    elif callback_id:
        message_ref = f"tg:callback:{callback_id}"
    elif message_id:
        message_ref = f"tg:message:{message_id}"
    else:
        message_ref = f"tg:log:{line_digest(line)[:12]}"

    title = (text or "Telegram inbound update").strip()
    issue_id = _regex_value(r"\b(ISSUE-\d+)\b", title)

    source: dict[str, Any] = {
        "channel": "telegram",
        "sessionKey": session_key,
        "messageRef": message_ref,
        "rawLogTime": line.get("time"),
        "rawLogLevel": line.get("level"),
        "rawLogSubsystem": line.get("subsystem"),
        "rawLogMessage": message,
    }
    if chat is not None:
        source["chatId"] = chat
    if user_id is not None:
        source["userId"] = user_id
    if update_id is not None:
        source["telegramUpdateId"] = update_id
    if callback_id is not None:
        source["telegramCallbackId"] = callback_id
    source["flowId"] = session_key
    source["flowStep"] = message_ref
    source["sessionReplayKey"] = f"{session_key}:{message_ref}"
    source["replayKey"] = f"telegram:{line_digest(line)[:12]}"

    payload: dict[str, Any] = {
        "title": title,
        "message": text,
        "kind": "default_chat",
        "workflow": "operate-and-grow",
        "executionMode": "AUTO",
        "priority": "medium",
        "source": source,
        "flow": {
            "flowId": session_key,
            "flowStep": message_ref,
            "sessionReplayKey": source["sessionReplayKey"],
            "replayKey": source["replayKey"],
        },
    }
    if issue_id is not None:
        payload["issueId"] = issue_id
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(agentos.DEFAULT_DB_PATH))
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--file", default=None, help="Read a saved channels logs JSON snapshot from this file")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    parser.add_argument("--allowed-agents", default="gemini")
    parser.add_argument("--requested-agent", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def process_snapshot(
    conn,
    snapshot: dict[str, Any],
    *,
    allowed_agents: list[str],
    requested_agent: str | None,
    dry_run: bool,
    state_file: Path,
) -> dict[str, Any]:
    lines = snapshot.get("lines", [])
    cursor = load_cursor(state_file)
    new_lines = split_new_lines([line for line in lines if isinstance(line, dict)], cursor)

    processed: list[dict[str, Any]] = []
    skipped = 0
    last_seen: dict[str, Any] | None = None

    for line in new_lines:
        last_seen = line
        payload = build_intake_payload_from_log(line)
        if payload is None:
            skipped += 1
            continue
        result = agentos.ingest_channel_event(
            conn,
            payload,
            allowed_agents=allowed_agents,
            requested_agent=requested_agent,
            dry_run=dry_run,
        )
        processed.append(result)

    if last_seen is not None and not dry_run:
        save_cursor(state_file, last_time=str(last_seen.get("time") or ""), last_digest=line_digest(last_seen))

    return {
        "status": "dry_run" if dry_run else "ok",
        "channel": snapshot.get("channel", "telegram"),
        "snapshotFile": snapshot.get("file"),
        "seenLines": len(new_lines),
        "processed": len(processed),
        "skipped": skipped,
        "results": processed,
        "cursorUpdated": bool(last_seen is not None and not dry_run),
        "cursor": cursor,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    allowed_agents = [item for item in args.allowed_agents.split(",") if item]
    if not allowed_agents:
        allowed_agents = ["gemini"]

    snapshot = load_snapshot(args.file, container=args.container, profile=args.profile, limit=args.limit)
    if snapshot.get("status") == "skipped":
        print(json.dumps(snapshot, indent=2, ensure_ascii=True))
        return 0

    db_path = Path(args.db)
    agentos.init_db(db_path)
    conn = agentos.open_db(db_path)
    try:
        result = process_snapshot(
            conn,
            snapshot,
            allowed_agents=allowed_agents,
            requested_agent=args.requested_agent,
            dry_run=args.dry_run,
            state_file=Path(args.state_file),
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
