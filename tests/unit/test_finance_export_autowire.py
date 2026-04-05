from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "finance_export_autowire.py"


def load_module():
    spec = importlib.util.spec_from_file_location("finance_export_autowire", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FinanceExportAutowireTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.module = load_module()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolve_candidate_prefers_recommended_source(self) -> None:
        report = {
            "recommendedSource": {"path": "/tmp/ledger.csv", "score": 100},
            "candidateCount": 1,
        }
        resolved = self.module.resolve_candidate(report)
        self.assertEqual(resolved, Path("/tmp/ledger.csv"))

    def test_dry_run_writes_state_without_wiring(self) -> None:
        state_file = self.work_dir / "autowire.json"
        fake_discovery = {
            "candidateCount": 0,
            "searchRoots": [str(self.work_dir)],
            "recommendedSource": None,
        }
        with mock.patch.object(
            self.module,
            "discover_finance_export",
            return_value=fake_discovery,
        ), mock.patch.object(self.module, "run_watchdog") as run_watchdog:
            run_watchdog.return_value = {"status": "stable"}
            rc = self.module.main(["--dry-run", "--state-file", str(state_file)])

        self.assertEqual(rc, 0)
        self.assertTrue(state_file.exists())
        payload = state_file.read_text(encoding="utf-8")
        self.assertIn("dry_run", payload)
        run_watchdog.assert_called_once()

    def test_wires_candidate_then_publishes_capture(self) -> None:
        state_file = self.work_dir / "autowire.json"
        candidate = self.work_dir / "finance" / "ledger.csv"
        candidate.parent.mkdir(parents=True)
        candidate.write_text("date,amount\n2026-04-05,100\n", encoding="utf-8")
        fake_discovery = {
            "candidateCount": 1,
            "searchRoots": [str(self.work_dir)],
            "recommendedSource": {"path": str(candidate), "score": 100},
        }

        with mock.patch.object(
            self.module,
            "discover_finance_export",
            return_value=fake_discovery,
        ), mock.patch.object(self.module, "install_dropin") as install_dropin, mock.patch.object(
            self.module, "run_weekly_capture"
        ) as run_weekly_capture, mock.patch.object(self.module, "run_watchdog") as run_watchdog:
            install_dropin.return_value = {"returncode": 0, "stdout": "ok", "stderr": ""}
            run_weekly_capture.return_value = {
                "returncode": 0,
                "commit": "abc123",
                "stdout": "commit: abc123",
                "stderr": "",
            }
            run_watchdog.return_value = {"status": "stable"}
            rc = self.module.main(["--state-file", str(state_file)])

        self.assertEqual(rc, 0)
        install_dropin.assert_called_once()
        run_weekly_capture.assert_called_once()
        run_watchdog.assert_called_once()
        self.assertTrue(state_file.exists())
        self.assertIn("wired_and_published", state_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
