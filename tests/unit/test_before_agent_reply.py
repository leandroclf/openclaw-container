from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from scripts import before_agent_reply


class BeforeAgentReplyTestCase(unittest.TestCase):
    def test_telegram_reply_sanitizes_large_json(self) -> None:
        text = '{"payload":"' + ("x" * 2000) + '"}'
        formatted = before_agent_reply.format_reply(
            text,
            channel="telegram",
            artifact_ref="artifact://reply-json",
        )
        self.assertIn("Large JSON payload omitted", formatted)
        self.assertIn("artifact://reply-json", formatted)

    def test_whatsapp_reply_uses_channel_safe_headings(self) -> None:
        text = """# Update

- item one
- item two
"""
        formatted = before_agent_reply.format_reply(text, channel="whatsapp")
        self.assertIn("*Update*", formatted)
        self.assertIn("- item one", formatted)

    def test_script_help_runs(self) -> None:
        script = Path(__file__).resolve().parents[2] / "scripts" / "before_agent_reply.py"
        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("Normalize outbound replies before they leave OpenClaw", completed.stdout)


if __name__ == "__main__":
    unittest.main()
