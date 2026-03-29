#!/usr/bin/env python3
"""Normalize a channel payload into the canonical Agent OS task packet."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import agentos


def load_payload(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise agentos.ValidationError("channel intake payload must be a JSON object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(agentos.DEFAULT_DB_PATH))
    parser.add_argument("--file", default=None, help="Read JSON from this file; stdin is used otherwise")
    parser.add_argument("--allowed-agents", default="gemini")
    parser.add_argument("--requested-agent", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = load_payload(args.file)
    allowed_agents = [item for item in args.allowed_agents.split(",") if item]

    db_path = Path(args.db)
    agentos.init_db(db_path)
    conn = agentos.open_db(db_path)
    try:
        result = agentos.ingest_channel_event(
            conn,
            payload,
            allowed_agents=allowed_agents,
            requested_agent=args.requested_agent,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
