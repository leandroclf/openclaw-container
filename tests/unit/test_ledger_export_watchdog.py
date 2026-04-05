from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import ledger_export_watchdog


class LedgerExportWatchdogTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "ledger-export-watchdog.json"
        self.ledger_path = Path(self.temp_dir.name) / "ledger.csv"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolve_ledger_export_path_prefers_explicit_argument(self) -> None:
        with mock.patch.dict("os.environ", {"OPENCLAW_LEDGER_EXPORT_PATH": "/tmp/env-ledger.csv"}, clear=False):
            resolved = ledger_export_watchdog.resolve_ledger_export_path("/tmp/explicit-ledger.csv")
        self.assertEqual(str(resolved), "/tmp/explicit-ledger.csv")

    def test_resolve_ledger_export_path_falls_back_to_environment_then_canonical(self) -> None:
        with mock.patch.dict("os.environ", {"OPENCLAW_LEDGER_EXPORT_PATH": "/tmp/env-ledger.csv"}, clear=False):
            resolved = ledger_export_watchdog.resolve_ledger_export_path(None)
        self.assertEqual(str(resolved), "/tmp/env-ledger.csv")

        with mock.patch.dict("os.environ", {"OPENCLAW_LEDGER_EXPORT_PATH": ""}, clear=False):
            resolved = ledger_export_watchdog.resolve_ledger_export_path(None)
        self.assertEqual(str(resolved), str(ledger_export_watchdog.DEFAULT_CANONICAL_LEDGER))

    def test_snapshot_and_classify_transition(self) -> None:
        self.ledger_path.write_text("date,amount\n2026-04-05,100\n", encoding="utf-8")
        snapshot = ledger_export_watchdog.snapshot_ledger_export(self.ledger_path)
        self.assertTrue(snapshot["exists"])
        self.assertEqual(snapshot["size"], len("date,amount\n2026-04-05,100\n"))
        self.assertEqual(len(snapshot["sha256"]), 64)

        previous = {}
        self.assertEqual(ledger_export_watchdog.classify_change(previous, snapshot), "appeared")
        self.assertEqual(
            ledger_export_watchdog.classify_change(snapshot, {"path": snapshot["path"], "exists": False, "observedAt": snapshot["observedAt"]}),
            "disappeared",
        )
        updated = dict(snapshot)
        updated["sha256"] = "f" * 64
        self.assertEqual(ledger_export_watchdog.classify_change(snapshot, updated), "updated")
        self.assertEqual(ledger_export_watchdog.classify_change(snapshot, snapshot), "stable")

    def test_run_watchdog_dry_run_does_not_persist_or_alert(self) -> None:
        self.ledger_path.write_text("date,amount\n2026-04-05,100\n", encoding="utf-8")
        with mock.patch.object(ledger_export_watchdog, "send_telegram_alert") as send_alert:
            report = ledger_export_watchdog.run_watchdog(
                ledger_export=self.ledger_path,
                state_file=self.state_file,
                alert_target="",
                container="openclaw",
                profile="prod",
                dry_run=True,
            )

        self.assertEqual(report["changeType"], "appeared")
        self.assertFalse(self.state_file.exists())
        send_alert.assert_not_called()

    def test_run_watchdog_persists_state_and_alerts_on_appearance(self) -> None:
        self.ledger_path.write_text("date,amount\n2026-04-05,100\n", encoding="utf-8")
        with mock.patch.object(
            ledger_export_watchdog,
            "docker_available",
            return_value=True,
        ), mock.patch.object(ledger_export_watchdog, "format_telegram_alert", return_value="formatted"), mock.patch.object(
            ledger_export_watchdog.subprocess,
            "run",
        ) as run_mock:
            run_mock.return_value = mock.Mock(returncode=0, stderr="", stdout="")
            report = ledger_export_watchdog.run_watchdog(
                ledger_export=self.ledger_path,
                state_file=self.state_file,
                alert_target="123456",
                container="openclaw",
                profile="prod",
                dry_run=False,
            )

        self.assertEqual(report["changeType"], "appeared")
        self.assertTrue(self.state_file.exists())
        persisted = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(persisted["lastChangeType"], "appeared")
        self.assertTrue(report["alert"]["sent"])


if __name__ == "__main__":
    unittest.main()
