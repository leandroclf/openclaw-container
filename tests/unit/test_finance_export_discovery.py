from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.finance_export_discovery import discover_finance_exports


class FinanceExportDiscoveryTestCase(unittest.TestCase):
    def test_discovers_supported_candidate_and_prefers_ledger_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finance_dir = root / "reports" / "finance"
            finance_dir.mkdir(parents=True)
            ignored = finance_dir / "notes.md"
            ignored.write_text("not an export\n", encoding="utf-8")
            candidate = finance_dir / "monthly-ledger.csv"
            candidate.write_text("date,amount\n2026-04-05,100\n", encoding="utf-8")

            with mock.patch.dict(
                "os.environ",
                {"OPENCLAW_LEDGER_EXPORT_SEARCH_PATHS": str(root)},
                clear=False,
            ):
                report = discover_finance_exports(max_depth=4, limit=5)

        self.assertEqual(report["candidateCount"], 1)
        self.assertEqual(report["recommendedSource"]["path"], str(candidate))
        self.assertGreater(report["recommendedSource"]["score"], 0)
        self.assertIn("supported format .csv", report["recommendedSource"]["reasons"])

    def test_returns_empty_recommendation_when_no_candidate_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch.dict(
                "os.environ",
                {"OPENCLAW_LEDGER_EXPORT_SEARCH_PATHS": str(root)},
                clear=False,
            ):
                report = discover_finance_exports(max_depth=2, limit=5)

        self.assertEqual(report["candidateCount"], 0)
        self.assertIsNone(report["recommendedSource"])


if __name__ == "__main__":
    unittest.main()
