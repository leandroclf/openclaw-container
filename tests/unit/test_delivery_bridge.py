from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from scripts import agentos, delivery_execution_bridge, delivery_handoff_consumer, delivery_result_reconcile


class DeliveryBridgeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bridge_dir = Path(self.temp_dir.name)
        self.db_path = self.bridge_dir / "agentos.db"
        agentos.init_db(self.db_path)
        self.conn = agentos.open_db(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        self.temp_dir.cleanup()

    def write_request(self, *, repo_can_execute: bool = True, request_id: str = "req-1") -> None:
        created_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        payload = {
            "requestId": request_id,
            "createdAt": created_at,
            "status": "pending_internal_consumption",
            "task": {
                "taskId": "task-1",
                "issueId": "ISSUE-001",
                "title": "Execute ISSUE-001",
                "kind": "code_impl",
                "workflow": "build-mvp",
                "executionMode": "AUTO",
                "priority": "high",
                "repo": "/tmp/repo",
                "branch": "feature/demo",
                "acceptance": {"required": ["test", "commit", "pr_or_pr_update"], "ciMustPass": True},
            },
            "routing": {"requestedAgent": "codex", "effectiveAgent": "gemini", "reason": "allowedAgents restricts execution to gemini"},
            "repoReadiness": {
                "exists": True,
                "isGit": True,
                "currentBranch": "main",
                "remoteOrigin": "git@github.com:example/repo.git",
                "dirtyFiles": [],
                "canExecuteMutations": repo_can_execute,
                "denyReason": None if repo_can_execute else "repo_dirty",
            },
        }
        (self.bridge_dir / "delivery-execution-request.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_delivery_consumer_ready(self) -> None:
        self.write_request()
        # run script-style function through argv patch
        with mock.patch("sys.argv", ["delivery_handoff_consumer.py", "--bridge-dir", str(self.bridge_dir)]):
            delivery_handoff_consumer.main()
        state = json.loads((self.bridge_dir / "delivery-handoff-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "ready")

    def test_delivery_consumer_blocks_dirty_repo(self) -> None:
        self.write_request(repo_can_execute=False)
        with mock.patch("sys.argv", ["delivery_handoff_consumer.py", "--bridge-dir", str(self.bridge_dir)]):
            delivery_handoff_consumer.main()
        state = json.loads((self.bridge_dir / "delivery-handoff-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "blocked")
        self.assertIn("Repo not ready for execution", state["notes"][0])

    def test_delivery_execution_bridge_blocks_when_internal_primary(self) -> None:
        self.write_request()
        (self.bridge_dir / "delivery-handoff-state.json").write_text(
            json.dumps({"status": "ready", "lastActivatedRequestId": None}, indent=2) + "\n",
            encoding="utf-8",
        )
        cron_payload = {"jobs": [{"id": "cron-1", "name": "Autopilot sequential delivery cycle", "enabled": True, "state": {}}]}
        with mock.patch.object(delivery_execution_bridge, "run_json", return_value=cron_payload):
            with mock.patch("sys.argv", ["delivery_execution_bridge.py", "--bridge-dir", str(self.bridge_dir)]):
                delivery_execution_bridge.main()
        intent = json.loads((self.bridge_dir / "delivery-execution-intent.json").read_text(encoding="utf-8"))
        self.assertEqual(intent["status"], "blocked")
        self.assertTrue(intent["guards"]["internalDeliveryPrimary"])

    def test_delivery_reconcile_completes_executor_and_parent(self) -> None:
        routing = agentos.resolve_routing(kind="planning", allowed_agents=["gemini"], requested_agent="gemini")
        parent = agentos.default_task(
            kind="planning",
            title="ISSUE-001 planning",
            workflow="build-mvp",
            execution_mode="AUTO",
            priority="high",
            source={"channel": "board"},
            routing=routing.as_dict(),
            acceptance={"required": ["report"], "ciMustPass": False},
            issue_id="ISSUE-001",
            repo="/tmp/repo",
            branch="feature/demo",
        )
        parent = agentos.enqueue_task(self.conn, parent)
        child_routing = agentos.resolve_routing(kind="code_impl", allowed_agents=["gemini"], requested_agent="codex")
        child = agentos.default_task(
            kind="code_impl",
            title="ISSUE-001 exec",
            workflow="build-mvp",
            execution_mode="AUTO",
            priority="high",
            source={"channel": "board", "parentTaskId": parent["taskId"], "role": "executor"},
            routing=child_routing.as_dict(),
            acceptance={"required": ["test", "commit", "pr_or_pr_update"], "ciMustPass": True},
            issue_id="ISSUE-001",
            repo="/tmp/repo",
            branch="feature/demo",
        )
        child = agentos.enqueue_task(self.conn, child)
        request = {
            "requestId": "req-1",
            "createdAt": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "status": "pending_internal_consumption",
            "task": {
                "taskId": child["taskId"],
                "issueId": "ISSUE-001",
                "title": child["title"],
                "kind": "code_impl",
                "workflow": "build-mvp",
                "executionMode": "AUTO",
                "priority": "high",
                "repo": "/tmp/repo",
                "branch": "feature/demo",
                "acceptance": child["acceptance"],
            },
            "repoReadiness": {"canExecuteMutations": True},
        }
        result = {
            "requestId": "req-1",
            "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "succeeded",
            "tests": ["python3 -m unittest"],
            "commit": "abc1234",
            "pr": "https://github.com/example/repo/pull/1",
            "ciStatus": "pass",
        }
        (self.bridge_dir / "delivery-execution-request.json").write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
        (self.bridge_dir / "delivery-execution-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

        with mock.patch("sys.argv", ["delivery_result_reconcile.py", "--db", str(self.db_path), "--bridge-dir", str(self.bridge_dir)]):
            delivery_result_reconcile.main()

        child_after = agentos.get_task(self.conn, child["taskId"])
        parent_after = agentos.get_task(self.conn, parent["taskId"])
        self.assertEqual(child_after["state"]["status"], "succeeded")
        self.assertEqual(parent_after["state"]["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
