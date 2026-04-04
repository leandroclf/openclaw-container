#!/usr/bin/env python3
"""Normalize outbound replies before they leave OpenClaw."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import agentos


CHANNEL_LIMITS = {
    "telegram": 3500,
    "slack": 4000,
    "discord": 1900,
    "whatsapp": 4000,
}


def read_input(args: argparse.Namespace) -> str:
    if args.message is not None:
        return args.message
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    return sys.stdin.read()


def collapse_blank_lines(text: str) -> str:
    lines: list[str] = []
    previous_blank = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        blank = not line.strip()
        if blank:
            if previous_blank:
                continue
            lines.append("")
            previous_blank = True
            continue
        lines.append(line.strip())
        previous_blank = False
    return "\n".join(lines).strip()


def rewrite_heading(line: str, channel: str) -> str:
    heading = re.sub(r"^\s*#{1,6}\s+", "", line).strip()
    if not heading:
        return ""
    if channel == "discord":
        return f"**{heading}**"
    if channel in {"telegram", "slack", "whatsapp"}:
        return f"*{heading}*"
    return heading


def normalize_for_channel(text: str, channel: str, artifact_ref: str | None = None) -> str:
    channel = channel.lower()
    normalized = collapse_blank_lines(text)
    if not normalized:
        return ""

    rewritten: list[str] = []
    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            rewritten.append("")
            continue
        if re.match(r"^\s*#{1,6}\s+", line):
            heading = rewrite_heading(line, channel)
            if heading:
                rewritten.append(heading)
            continue
        if re.match(r"^\s*\|.*\|\s*$", line):
            pieces = [part.strip() for part in line.strip("|").split("|")]
            pieces = [piece for piece in pieces if piece and not re.fullmatch(r":?-{3,}:?", piece)]
            if pieces:
                rewritten.append("- " + " / ".join(pieces))
            continue
        rewritten.append(line)

    normalized = "\n".join(rewritten).strip()
    limit = CHANNEL_LIMITS.get(channel, 4000)
    if len(normalized) <= limit:
        return normalized

    artifact_ref = artifact_ref or "artifact://reply"
    truncated = normalized[: limit - 80].rstrip()
    return f"{truncated}\n\n... truncated for {channel}; see {artifact_ref}"


def format_reply(text: str, *, channel: str, artifact_ref: str | None = None, header: str | None = None) -> str:
    channel = channel.lower().strip()
    normalized = collapse_blank_lines(text)
    if channel == "telegram":
        sanitized = agentos.sanitize_telegram_text(normalized, artifact_ref=artifact_ref)
        parts = agentos.prepare_telegram_envelope(
            sanitized,
            header=header,
            artifact_ref=artifact_ref,
            hard_limit=CHANNEL_LIMITS["telegram"],
            target_limit=2800,
        )
        message = parts[0] if parts else ""
        if len(parts) > 1:
            ref = artifact_ref or "artifact://reply"
            message = f"{message}\n\n... truncated into {len(parts)} parts; see {ref}"
        return normalize_for_channel(message, channel, artifact_ref=artifact_ref)
    return normalize_for_channel(normalized, channel, artifact_ref=artifact_ref)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True, choices=["telegram", "slack", "discord", "whatsapp"])
    parser.add_argument("--message", default=None)
    parser.add_argument("--file", default=None)
    parser.add_argument("--artifact-ref", default=None)
    parser.add_argument("--header", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    text = read_input(args)
    print(
        format_reply(
            text,
            channel=args.channel,
            artifact_ref=args.artifact_ref,
            header=args.header,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
