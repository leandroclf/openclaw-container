from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class OperationsAssetContractTests(unittest.TestCase):
    def test_compose_templates_exist(self) -> None:
        required = [
            ROOT / "compose" / "docker-compose.blue-green.yml",
            ROOT / "compose" / "blue.env.example",
            ROOT / "compose" / "green.env.example",
        ]
        for path in required:
            self.assertTrue(path.exists(), f"missing compose asset: {path}")

    def test_compose_guardrails_present(self) -> None:
        compose_text = (ROOT / "compose" / "docker-compose.blue-green.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("read_only: true", compose_text)
        self.assertIn("cap_drop:", compose_text)
        self.assertIn("no-new-privileges:true", compose_text)
        self.assertIn("openclaw-green", compose_text)

    def test_promotion_checklist_exists(self) -> None:
        path = ROOT / "docs" / "operations" / "PROMOTION_ROLLBACK_CHECKLIST.md"
        self.assertTrue(path.exists(), f"missing checklist: {path}")
        text = path.read_text(encoding="utf-8")
        self.assertIn("Pre-promotion baseline", text)
        self.assertIn("Rollback execution", text)


if __name__ == "__main__":
    unittest.main()
