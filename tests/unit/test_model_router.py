from __future__ import annotations

import unittest

from tests.common.import_model_router import load_model_router


class ModelRouterUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.router = load_model_router()

    def test_unique_preserve_order(self) -> None:
        result = self.router.unique_preserve_order(["a", "b", "a", "c", "b"])
        self.assertEqual(result, ["a", "b", "c"])

    def test_parse_json_payload_with_log_prefix(self) -> None:
        payload = "INFO header\n{\"ok\": true, \"x\": 1}"
        parsed = self.router.parse_json_payload(payload)
        self.assertEqual(parsed["ok"], True)
        self.assertEqual(parsed["x"], 1)

    def test_parse_json_payload_without_json_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            self.router.parse_json_payload("no json here")

    def test_filter_by_modalities(self) -> None:
        candidates = [
            ("m1", {"modalities": {"text": True, "image": False}}),
            ("m2", {"modalities": {"text": True, "image": True}}),
        ]
        filtered = self.router.filter_by_modalities(candidates, ["text", "image"])
        self.assertEqual([m for m, _ in filtered], ["m2"])

    def test_score_model_with_provider_and_probe_adjustments(self) -> None:
        model_cfg = {
            "provider": "openai-codex",
            "scores": {
                "coding": 9,
                "reasoning": 8,
                "latency": 7,
                "cost_efficiency": 6,
            },
        }
        objective_cfg = {
            "weights": {
                "coding": 0.5,
                "reasoning": 0.3,
                "latency": 0.1,
                "cost_efficiency": 0.1,
            }
        }
        final_score, details = self.router.score_model(
            model_key="openai-codex/gpt-5.3-codex",
            model_cfg=model_cfg,
            objective_cfg=objective_cfg,
            provider_state="ok",
            probe_state="ok",
        )
        expected_base = 9 * 0.5 + 8 * 0.3 + 7 * 0.1 + 6 * 0.1
        self.assertAlmostEqual(details["baseScore"], round(expected_base, 3))
        self.assertAlmostEqual(final_score, expected_base + 4.0)

    def test_enforce_required_fallbacks_front(self) -> None:
        updated, enforced, notes = self.router.enforce_required_fallbacks(
            scored_models=["m1", "m2", "m3", "m4"],
            primary="m1",
            fallbacks=["m3"],
            required_models=["m2", "m4", "m1"],
            position="front",
        )
        self.assertEqual(updated, ["m4", "m2", "m3"])
        self.assertEqual(enforced, ["m2", "m4"])
        self.assertTrue(any("already primary" in note for note in notes))

    def test_render_callbacks(self) -> None:
        rendered = self.router.render_callbacks(
            [
                "docker exec {container} openclaw --profile {profile} status",
                "echo {container}:{profile}",
            ],
            container="openclaw-next",
            profile="prod",
        )
        self.assertEqual(
            rendered,
            [
                "docker exec openclaw-next openclaw --profile prod status",
                "echo openclaw-next:prod",
            ],
        )


if __name__ == "__main__":
    unittest.main()
