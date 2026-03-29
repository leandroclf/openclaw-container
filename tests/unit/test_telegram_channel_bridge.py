from __future__ import annotations

import io
import json
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from scripts import agentos, telegram_channel_bridge


class TelegramChannelBridgeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "agentos.db"
        self.snapshot_path = Path(self.temp_dir.name) / "telegram-logs.json"
        self.state_file = Path(self.temp_dir.name) / "telegram.cursor.json"
        agentos.init_db(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_snapshot(self, snapshot: dict) -> None:
        self.snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    def test_build_intake_payload_from_received_log(self) -> None:
        payload = telegram_channel_bridge.build_intake_payload_from_log(
            {
                "time": "2026-03-29T20:12:00.000+00:00",
                "level": "info",
                "subsystem": "gateway/channels/telegram",
                "message": "telegram received update_id=7788 chat=343551192 message=441 text=ISSUE-007 keep monitoring",
                "raw": "{}",
            }
        )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["source"]["channel"], "telegram")
        self.assertEqual(payload["source"]["sessionKey"], "telegram:chat:343551192")
        self.assertEqual(payload["source"]["messageRef"], "tg:update:7788")
        self.assertEqual(payload["issueId"], "ISSUE-007")
        self.assertIn("keep monitoring", payload["title"])

    def test_build_intake_payload_skips_outbound_send_message(self) -> None:
        payload = telegram_channel_bridge.build_intake_payload_from_log(
            {
                "time": "2026-03-29T20:09:06.172+00:00",
                "level": "info",
                "subsystem": "gateway/channels/telegram",
                "message": "telegram sendMessage ok chat=343551192 message=2720",
                "raw": "{}",
            }
        )
        self.assertIsNone(payload)

    def test_process_snapshot_dry_run_and_cursor_is_not_advanced(self) -> None:
        self.write_snapshot(
            {
                "file": "/tmp/openclaw/openclaw-2026-03-29.log",
                "channel": "telegram",
                "lines": [
                    {
                        "time": "2026-03-29T20:09:06.172+00:00",
                        "level": "info",
                        "subsystem": "gateway/channels/telegram",
                        "message": "telegram sendMessage ok chat=343551192 message=2720",
                        "raw": "{}",
                    },
                    {
                        "time": "2026-03-29T20:12:00.000+00:00",
                        "level": "info",
                        "subsystem": "gateway/channels/telegram",
                        "message": "telegram received update_id=7788 chat=343551192 message=441 text=ISSUE-007 keep monitoring",
                        "raw": "{}",
                    },
                ],
            }
        )

        conn = agentos.open_db(self.db_path)
        try:
            result = telegram_channel_bridge.process_snapshot(
                conn,
                json.loads(self.snapshot_path.read_text(encoding="utf-8")),
                allowed_agents=["gemini"],
                requested_agent=None,
                dry_run=True,
                state_file=self.state_file,
            )
        finally:
            conn.close()

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["seenLines"], 2)
        self.assertEqual(result["status"], "dry_run")
        self.assertFalse(self.state_file.exists())
        conn = agentos.open_db(self.db_path)
        try:
            self.assertEqual(agentos.list_tasks(conn), [])
        finally:
            conn.close()

    def test_main_reads_snapshot_file(self) -> None:
        self.write_snapshot(
            {
                "file": "/tmp/openclaw/openclaw-2026-03-29.log",
                "channel": "telegram",
                "lines": [
                    {
                        "time": "2026-03-29T20:12:00.000+00:00",
                        "level": "info",
                        "subsystem": "gateway/channels/telegram",
                        "message": "telegram received update_id=9001 chat=343551192 message=442 text=Please review ISSUE-007",
                        "raw": "{}",
                    }
                ],
            }
        )

        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            rc = telegram_channel_bridge.main(
                [
                    "--db",
                    str(self.db_path),
                    "--file",
                    str(self.snapshot_path),
                    "--state-file",
                    str(self.state_file),
                    "--dry-run",
                ]
            )

        self.assertEqual(rc, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["processed"], 1)
        self.assertIn("Please review ISSUE-007", result["results"][0]["task"]["title"])

    def test_bridge_runs_directly_as_script(self) -> None:
        script = Path(__file__).resolve().parents[2] / "scripts" / "telegram_channel_bridge.py"
        completed = subprocess.run(
            [str(script), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("Poll Telegram channel logs", completed.stdout)


if __name__ == "__main__":
    unittest.main()
