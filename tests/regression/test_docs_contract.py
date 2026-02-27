from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DocumentationContractTests(unittest.TestCase):
    def test_guardrail_docs_exist(self) -> None:
        required = [
            ROOT / "docs" / "operations" / "PRODUCTION_CHANGE_POLICY.md",
            ROOT / "docs" / "operations" / "BLUE_GREEN_WSL_DOCKER_DESKTOP.md",
            ROOT / "docs" / "architecture" / "01-target-architecture.md",
            ROOT / "docs" / "architecture" / "02-phased-implementation-plan.md",
        ]
        for path in required:
            self.assertTrue(path.exists(), f"missing required doc: {path}")

    def test_production_policy_contains_non_downtime_controls(self) -> None:
        policy = (ROOT / "docs" / "operations" / "PRODUCTION_CHANGE_POLICY.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Never stop/remove `openclaw`", policy)
        self.assertIn("openclaw-next", policy)
        self.assertIn("docker context show", policy)
        self.assertIn("Never run candidate with production Telegram bot token", policy)

    def test_agenda_docs_linked_from_root_readme(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/operations/PRODUCTION_CHANGE_POLICY.md", readme)
        self.assertIn("docs/operations/PROMOTION_ROLLBACK_CHECKLIST.md", readme)
        self.assertIn("docs/architecture/README.md", readme)


if __name__ == "__main__":
    unittest.main()
