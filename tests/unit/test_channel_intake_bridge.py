from __future__ import annotations

import contextlib
import io
import json
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from scripts import agentos, channel_intake_bridge


class ChannelIntakeBridgeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "agentos.db"
        self.payload_path = Path(self.temp_dir.name) / "payload.json"
        agentos.init_db(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_payload(self, payload: dict) -> None:
        self.payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def test_bridge_emits_dry_run_canonical_task(self) -> None:
        self.write_payload(
            {
                "channel": "discord",
                "sessionId": "discord:thread-9",
                "messageId": "msg-9",
                "title": "Discord intake request",
                "kind": "planning",
                "workflow": "operate-and-grow",
                "executionMode": "AUTO",
                "priority": "medium",
            }
        )

        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            rc = channel_intake_bridge.main(
                [
                    "--db",
                    str(self.db_path),
                    "--file",
                    str(self.payload_path),
                    "--dry-run",
                ]
            )

        self.assertEqual(rc, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["task"]["source"]["channel"], "discord")
        self.assertEqual(result["task"]["source"]["sessionKey"], "discord:thread-9")
        self.assertEqual(result["task"]["source"]["messageRef"], "msg-9")

    def test_bridge_queues_and_deduplicates(self) -> None:
        self.write_payload(
            {
                "channel": "telegram",
                "sessionId": "tg:chat-21",
                "messageId": "msg-21",
                "title": "Telegram request",
                "kind": "default_chat",
                "workflow": "operate-and-grow",
                "executionMode": "AUTO",
                "priority": "low",
            }
        )

        stdout_first = io.StringIO()
        with mock.patch("sys.stdout", stdout_first):
            rc_first = channel_intake_bridge.main(["--db", str(self.db_path), "--file", str(self.payload_path)])
        self.assertEqual(rc_first, 0)
        first = json.loads(stdout_first.getvalue())
        self.assertEqual(first["status"], "queued")

        stdout_second = io.StringIO()
        with mock.patch("sys.stdout", stdout_second):
            rc_second = channel_intake_bridge.main(["--db", str(self.db_path), "--file", str(self.payload_path)])
        self.assertEqual(rc_second, 0)
        second = json.loads(stdout_second.getvalue())
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(second["canonicalTaskId"], first["task"]["taskId"])

    def test_bridge_runs_directly_as_script(self) -> None:
        script = Path(__file__).resolve().parents[2] / "scripts" / "channel_intake_bridge.py"
        completed = subprocess.run(
            [str(script), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("Normalize a channel payload", completed.stdout)


if __name__ == "__main__":
    unittest.main()
