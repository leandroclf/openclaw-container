from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import agentos


class AgentOSTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "agentos.db"
        self.workspace_root = Path(self.temp_dir.name) / "workspace"
        self.workspace_root.mkdir()
        agentos.init_db(self.db_path)
        self.conn = agentos.open_db(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        self.temp_dir.cleanup()

    def _make_task(self, *, kind: str = "code_impl") -> dict:
        routing = agentos.resolve_routing(kind=kind, allowed_agents=["gemini"], requested_agent="codex")
        return agentos.default_task(
            kind=kind,
            title="Demo task",
            workflow="build-mvp",
            execution_mode="AUTO",
            priority="high",
            source={"channel": "test"},
            routing=routing.as_dict(),
        )

    def test_task_validation_rejects_invalid_status(self) -> None:
        task = self._make_task()
        task["state"]["status"] = "not-valid"
        with self.assertRaises(agentos.ValidationError):
            agentos.validate_task(task)

    def test_queue_claim_heartbeat_expire_and_reclaim(self) -> None:
        task = agentos.enqueue_task(self.conn, self._make_task())
        claimed = agentos.claim_next_task(self.conn, worker_id="worker-1", lease_seconds=1)
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["taskId"], task["taskId"])
        refreshed = agentos.heartbeat(self.conn, task_id=task["taskId"], worker_id="worker-1", lease_seconds=1)
        self.assertEqual(refreshed["state"]["leaseOwner"], "worker-1")

        refreshed["state"]["leaseUntil"] = "2000-01-01T00:00:00Z"
        refreshed["timestamps"]["updatedAt"] = agentos.now_iso()
        agentos._upsert_task(self.conn, refreshed)
        self.conn.commit()

        expired = agentos.expire_leases(self.conn)
        self.assertEqual(expired, 1)

        reclaimed = agentos.claim_next_task(self.conn, worker_id="worker-2", lease_seconds=30)
        self.assertIsNotNone(reclaimed)
        self.assertEqual(reclaimed["state"]["leaseOwner"], "worker-2")

    def test_retry_exhaustion_moves_task_to_needs_human(self) -> None:
        task = self._make_task()
        task["budget"]["maxRetries"] = 1
        task = agentos.enqueue_task(self.conn, task)
        claimed = agentos.claim_next_task(self.conn, worker_id="worker-1")
        self.assertIsNotNone(claimed)

        retried = agentos.fail_task(
            self.conn,
            task_id=task["taskId"],
            worker_id="worker-1",
            reason="temporary",
            retryable=True,
        )
        self.assertEqual(retried["state"]["status"], "queued")
        self.assertIsNotNone(retried["state"]["nextRunAt"])
        self.assertIsNone(agentos.claim_next_task(self.conn, worker_id="worker-1"))

        retried["state"]["nextRunAt"] = "2000-01-01T00:00:00Z"
        retried["timestamps"]["updatedAt"] = agentos.now_iso()
        agentos._upsert_task(self.conn, retried)
        self.conn.commit()

        claimed_again = agentos.claim_next_task(self.conn, worker_id="worker-1")
        self.assertIsNotNone(claimed_again)
        needs_human = agentos.fail_task(
            self.conn,
            task_id=task["taskId"],
            worker_id="worker-1",
            reason="still failing",
            retryable=True,
        )
        self.assertEqual(needs_human["state"]["status"], "needs_human")

    def test_preflight_denies_forbidden_change_wave(self) -> None:
        def fake_runner(cmd: list[str]):
            if cmd[:3] == ["docker", "context", "show"]:
                return 0, "default", ""
            return 0, "ok", ""

        result = agentos.execute_preflight(
            change_wave={"infra": True, "policy": True, "routing": False, "auth": False},
            touches_production=False,
            is_parallel_candidate=False,
            reused_prod_volumes=False,
            reused_prod_workspace=False,
            used_prod_telegram_token_on_candidate=False,
            docker_runner=fake_runner,
        )
        self.assertFalse(result["preflight"]["allowedToProceed"])
        self.assertIn("infra+policy", result["preflight"]["denyReason"])

    def test_telegram_chunking_respects_hard_limit(self) -> None:
        text = "\n".join(f"line {idx} " + ("x" * 120) for idx in range(60))
        parts = agentos.prepare_telegram_envelope(text, header="[AgentOS]")
        self.assertGreater(len(parts), 1)
        for part in parts:
            self.assertLessEqual(len(part), 3500)
            self.assertIn("[part ", part)

    def test_telegram_envelope_sanitizes_large_json(self) -> None:
        large_json = '{"payload":"' + ("x" * 1500) + '"}'
        parts = agentos.prepare_telegram_envelope(
            large_json,
            header="[AgentOS]",
            artifact_ref="artifact://json",
        )
        self.assertEqual(len(parts), 1)
        self.assertIn("Large JSON payload omitted", parts[0])
        self.assertIn("artifact://json", parts[0])

    def test_intake_event_normalizes_source_and_deduplicates(self) -> None:
        payload = {
            "channel": "telegram",
            "sessionId": "tg:chat-17",
            "messageId": "msg-42",
            "title": "Telegram request",
            "kind": "planning",
            "workflow": "operate-and-grow",
            "executionMode": "AUTO",
            "priority": "medium",
            "requestedAgent": "gemini",
            "allowedAgents": ["gemini"],
        }

        first = agentos.ingest_channel_event(self.conn, payload)
        self.assertEqual(first["status"], "queued")
        task = first["task"]
        self.assertEqual(task["source"]["channel"], "telegram")
        self.assertEqual(task["source"]["sessionKey"], "tg:chat-17")
        self.assertEqual(task["source"]["messageRef"], "msg-42")
        self.assertTrue(task["source"]["dedupKey"].startswith("telegram:"))

        duplicate = agentos.ingest_channel_event(self.conn, payload)
        self.assertEqual(duplicate["status"], "duplicate")
        self.assertEqual(duplicate["canonicalTaskId"], task["taskId"])
        self.assertEqual(len(agentos.list_tasks(self.conn)), 1)

    def test_intake_event_dry_run_returns_canonical_task_without_enqueue(self) -> None:
        payload = {
            "source": {
                "channel": "slack",
                "session": "slack:thread-9",
                "messageRef": "slack-msg-9",
            },
            "title": "Slack intake request",
            "kind": "default_chat",
            "workflow": "operate-and-grow",
            "executionMode": "AUTO",
            "priority": "low",
        }

        result = agentos.ingest_channel_event(self.conn, payload, dry_run=True)
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["task"]["source"]["channel"], "slack")
        self.assertEqual(result["task"]["source"]["sessionKey"], "slack:thread-9")
        self.assertEqual(result["task"]["source"]["messageRef"], "slack-msg-9")
        self.assertEqual(agentos.list_tasks(self.conn), [])

    def test_intake_event_links_flow_metadata_and_child_task_ids(self) -> None:
        parent = agentos.enqueue_task(self.conn, self._make_task())
        parent_flow_before = dict(parent["flow"])
        payload = {
            "source": {
                "channel": "telegram",
                "sessionId": "tg:chat-77",
                "messageId": "msg-77",
                "parentTaskId": parent["taskId"],
                "flowId": "flow-77",
                "flowStep": "step-2",
                "sessionReplayKey": "tg:chat-77:msg-77",
                "replayKey": "telegram:reply-77",
            },
            "title": "Child task",
            "kind": "planning",
            "workflow": "operate-and-grow",
            "executionMode": "AUTO",
            "priority": "medium",
        }

        result = agentos.ingest_channel_event(self.conn, payload)
        self.assertEqual(result["status"], "queued")
        child = result["task"]
        self.assertEqual(child["source"]["parentTaskId"], parent["taskId"])
        self.assertEqual(child["source"]["flowId"], "flow-77")
        self.assertEqual(child["source"]["sessionReplayKey"], "tg:chat-77:msg-77")
        self.assertEqual(child["source"]["replayKey"], "telegram:reply-77")
        self.assertIn("flow", child)
        self.assertEqual(child["flow"]["parentTaskId"], parent["taskId"])
        self.assertEqual(child["flow"]["flowId"], "flow-77")
        self.assertNotIn("childTaskIds", child["flow"])

        parent_after = agentos.get_task(self.conn, parent["taskId"])
        self.assertIsNotNone(parent_after)
        assert parent_after is not None
        self.assertIn(child["taskId"], parent_after["flow"]["childTaskIds"])
        self.assertTrue(parent_after["flow"]["flowId"])
        self.assertEqual(parent_after["flow"]["sessionReplayKey"], parent_flow_before["sessionReplayKey"])
        self.assertEqual(parent_after["flow"]["replayKey"], parent_flow_before["replayKey"])
        self.assertEqual(parent_after["flow"]["flowStep"], "step-2")
        self.assertEqual(parent_after["source"]["sessionReplayKey"], parent_flow_before["sessionReplayKey"])
        self.assertEqual(parent_after["source"]["replayKey"], parent_flow_before["replayKey"])
        self.assertEqual(parent_after["source"]["flowStep"], "step-2")

    def test_routing_plan_links_to_model_router(self) -> None:
        plan = agentos.resolve_routing_plan(
            kind="code_impl",
            allowed_agents=["gemini"],
            requested_agent="codex",
            container="openclaw",
            profile="prod",
            probe=True,
        )
        self.assertEqual(plan.decision.objective, "coding_quality")
        self.assertEqual(plan.decision.effective_agent, "gemini")
        self.assertIn("--objective", plan.model_router_command)
        self.assertIn("coding_quality", plan.model_router_command)
        self.assertIn("--probe", plan.model_router_command)

    def test_supervisor_safe_mode_does_not_create_loops(self) -> None:
        sensitive_task = self._make_task(kind="policy_change")
        agentos.enqueue_task(self.conn, sensitive_task)
        supervisor = agentos.Supervisor(safe_mode=True, max_derived_tasks_per_root=2)
        result = supervisor.cycle(self.conn, agentos.list_tasks(self.conn))
        self.assertEqual(result.action, "observe_only")
        self.assertEqual(len(result.derived_tasks), 1)
        self.assertEqual(result.derived_tasks[0]["kind"], "policy_change")
        planning_tasks = [task for task in agentos.list_tasks(self.conn) if task["kind"] == "planning"]
        self.assertEqual(planning_tasks, [])

    def test_supervisor_blocks_denied_preflight(self) -> None:
        def fake_runner(cmd: list[str]):
            if cmd[:3] == ["docker", "context", "show"]:
                return 0, "default", ""
            return 0, "ok", ""

        task = self._make_task(kind="policy_change")
        task["preflight"] = {
            "touchesProduction": False,
            "changeWave": {"infra": True, "policy": True, "routing": False, "auth": False},
        }
        agentos.enqueue_task(self.conn, task)
        supervisor = agentos.Supervisor(safe_mode=False, docker_runner=fake_runner, shell_runner=fake_runner)
        result = supervisor.cycle(self.conn)
        blocked = agentos.get_task(self.conn, task["taskId"])
        self.assertEqual(result.blocked_tasks, [task["taskId"]])
        self.assertEqual(blocked["state"]["status"], "blocked")
        self.assertEqual(blocked["state"]["lastBlockerType"], "HARD_BLOCKER")
        self.assertIn("infra+policy", blocked["state"]["lastBlockerReason"])

    def test_supervisor_persists_planning_handoff_after_preflight_pass(self) -> None:
        def fake_runner(cmd: list[str]):
            if cmd[:3] == ["docker", "context", "show"]:
                return 0, "default", ""
            return 0, "ok", ""

        task = self._make_task(kind="policy_change")
        task["preflight"] = {
            "touchesProduction": False,
            "changeWave": {"infra": False, "policy": True, "routing": False, "auth": False},
        }
        agentos.enqueue_task(self.conn, task)
        supervisor = agentos.Supervisor(safe_mode=False, docker_runner=fake_runner, shell_runner=fake_runner)
        result = supervisor.cycle(self.conn)
        self.assertEqual(result.action, "processed_sensitive_queue")
        self.assertEqual(len(result.derived_tasks), 1)
        planning_tasks = [item for item in agentos.list_tasks(self.conn) if item["kind"] == "planning"]
        self.assertEqual(len(planning_tasks), 1)

        rows = self.conn.execute(
            "SELECT event_json FROM events WHERE task_id = ? AND event_type = 'task.handoff'",
            (task["taskId"],),
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn("planner", rows[0][0])

    def test_complete_requires_code_evidence(self) -> None:
        task = self._make_task(kind="code_impl")
        task["acceptance"] = {"required": ["test", "commit", "pr_or_pr_update"], "ciMustPass": True}
        task = agentos.enqueue_task(self.conn, task)
        claimed = agentos.claim_next_task(self.conn, worker_id="worker-1")
        self.assertIsNotNone(claimed)
        with self.assertRaises(agentos.ValidationError):
            agentos.complete_task(
                self.conn,
                task_id=task["taskId"],
                worker_id="worker-1",
                evidence_refs=["note:missing"],
            )
        completed = agentos.complete_task(
            self.conn,
            task_id=task["taskId"],
            worker_id="worker-1",
            evidence_refs=[
                "test:python3 -m unittest",
                "commit:abc1234",
                "pr:https://github.com/example/repo/pull/1",
                "ci:pass",
            ],
        )
        self.assertEqual(completed["state"]["status"], "succeeded")

    def test_run_registered_workflow_persists_report_and_completes(self) -> None:
        script_dir = self.workspace_root / "ops" / "multiagent" / "delivery" / "scripts"
        report_dir = self.workspace_root / "ops" / "multiagent" / "delivery"
        script_dir.mkdir(parents=True)
        report_dir.mkdir(parents=True, exist_ok=True)
        (script_dir / "ops_state_lint.py").write_text(
            "from pathlib import Path\n"
            "Path('ops/multiagent/delivery/ops-lint-report.md').write_text('ok\\n', encoding='utf-8')\n"
            "print('ops lint ok')\n",
            encoding="utf-8",
        )
        registry = Path(self.temp_dir.name) / "workflow_registry.json"
        registry.write_text(
            """
{
  "version": "test",
  "workflows": {
    "daily_ops_state_lint": {
      "kind": "ops_watchdog",
      "title": "Daily ops state lint",
      "priority": "low",
      "command": ["python3", "ops/multiagent/delivery/scripts/ops_state_lint.py"],
      "acceptanceRequired": ["report", "command"],
      "evidenceRefs": ["ops/multiagent/delivery/ops-lint-report.md"],
      "retryable": false
    }
  }
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        result = agentos.run_registered_workflow(
            self.conn,
            workflow_name="daily_ops_state_lint",
            workspace_root=self.workspace_root,
            registry_path=registry,
        )
        self.assertEqual(result["task"]["state"]["status"], "succeeded")
        self.assertTrue((report_dir / "ops-lint-report.md").exists())
        events = self.conn.execute(
            "SELECT event_type FROM events WHERE task_id=? ORDER BY created_at",
            (result["task"]["taskId"],),
        ).fetchall()
        event_types = [row[0] for row in events]
        self.assertIn("task.completed", event_types)

    def test_prepare_workflow_command_rewrites_hardcoded_workspace_path(self) -> None:
        script = self.workspace_root / "ops" / "multiagent" / "delivery" / "scripts" / "daily_summary_rotate.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("src = '/home/node/clawd/ops/multiagent/delivery/daily-summary.md'\n", encoding="utf-8")
        command, rewritten = agentos.prepare_workflow_command(
            ["python3", "ops/multiagent/delivery/scripts/daily_summary_rotate.py"],
            self.workspace_root,
        )
        self.assertIsNotNone(rewritten)
        self.assertEqual(command[0], "python3")
        self.assertEqual(command[1], str(rewritten))
        self.assertIn(str(self.workspace_root), rewritten.read_text(encoding="utf-8"))

    def test_parse_delivery_board_extracts_auto_issue_metadata(self) -> None:
        board = self.workspace_root / "ops" / "multiagent" / "delivery" / "board.md"
        board.parent.mkdir(parents=True, exist_ok=True)
        board.write_text(
            """
## AUTHORIZED
- Issue: [ISSUE-001] MVP de Enrichment B2B com OpenAlex
  - Execution Mode: AUTO
  - Owner: builder-repo
  - Repo: https://github.com/leandroclf/lf-openalex-enrichment-mvp

## TO REVIEW
- Issue: [ISSUE-900] Exemplo humano
  - Execution Mode: HUMAN
  - Owner: reviewer-delivery
""".strip()
            + "\n",
            encoding="utf-8",
        )
        issues = agentos.parse_delivery_board(board)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].issue_id, "ISSUE-001")
        self.assertEqual(issues[0].execution_mode, "AUTO")
        self.assertEqual(issues[0].owner, "builder-repo")

    def test_sync_delivery_board_enqueues_authorized_auto_issue_once(self) -> None:
        repo_dir = self.workspace_root / "projects" / "lf-openalex-enrichment-mvp"
        repo_dir.mkdir(parents=True)
        board = self.workspace_root / "ops" / "multiagent" / "delivery" / "board.md"
        board.parent.mkdir(parents=True, exist_ok=True)
        board.write_text(
            """
## AUTHORIZED
- Issue: [ISSUE-001] MVP de Enrichment B2B com OpenAlex
  - Execution Mode: AUTO
  - Owner: builder-repo
  - Repo: https://github.com/leandroclf/lf-openalex-enrichment-mvp
""".strip()
            + "\n",
            encoding="utf-8",
        )
        first = agentos.sync_delivery_board(
            self.conn,
            workspace_root=self.workspace_root,
            board_path=board,
            sections={"AUTHORIZED"},
            allowed_agents=["gemini"],
        )
        self.assertEqual(len(first["created"]), 1)
        task = agentos.list_tasks(self.conn)[0]
        self.assertEqual(task["kind"], "planning")
        self.assertEqual(task["issueId"], "ISSUE-001")
        self.assertEqual(task["repo"], str(repo_dir))

        second = agentos.sync_delivery_board(
            self.conn,
            workspace_root=self.workspace_root,
            board_path=board,
            sections={"AUTHORIZED"},
            allowed_agents=["gemini"],
        )
        self.assertEqual(len(second["created"]), 0)
        self.assertEqual(second["skipped"][0]["reason"], "active_task_exists")

    def test_supervisor_promotes_board_planning_to_executor_task(self) -> None:
        repo_dir = self.workspace_root / "projects" / "lf-openalex-enrichment-mvp"
        repo_dir.mkdir(parents=True)
        issue = agentos.DeliveryBoardIssue(
            section="AUTHORIZED",
            issue_id="ISSUE-001",
            title="MVP de Enrichment B2B com OpenAlex",
            execution_mode="AUTO",
            owner="builder-repo",
            workflow="build-mvp",
            priority="high",
            repo="https://github.com/leandroclf/lf-openalex-enrichment-mvp",
        )
        root_task = agentos.build_issue_task(issue, workspace_root=self.workspace_root, allowed_agents=["gemini"])
        agentos.enqueue_task(self.conn, root_task)

        supervisor = agentos.Supervisor(safe_mode=False)
        result = supervisor.cycle(self.conn)
        self.assertEqual(result.action, "processed_sensitive_queue")
        executor_tasks = [item for item in agentos.list_tasks(self.conn) if item["kind"] == "code_impl"]
        self.assertEqual(len(executor_tasks), 1)
        self.assertEqual(executor_tasks[0]["issueId"], "ISSUE-001")
        self.assertEqual(executor_tasks[0]["acceptance"]["ciMustPass"], True)

        root = agentos.get_task(self.conn, root_task["taskId"])
        self.assertEqual(root["state"]["status"], "blocked")
        self.assertIn("awaiting_executor:", root["state"]["lastBlockerReason"])

    def test_export_delivery_handoff_writes_request_for_clean_repo(self) -> None:
        repo_dir = self.workspace_root / "projects" / "lf-openalex-enrichment-mvp"
        repo_dir.mkdir(parents=True)
        agentos.run_capture(["git", "init", "-b", "main"], repo_dir)
        agentos.run_capture(["git", "config", "user.name", "Test"], repo_dir)
        agentos.run_capture(["git", "config", "user.email", "test@example.com"], repo_dir)
        (repo_dir / "README.md").write_text("demo\n", encoding="utf-8")
        agentos.run_capture(["git", "add", "README.md"], repo_dir)
        agentos.run_capture(["git", "commit", "-m", "init"], repo_dir)
        agentos.run_capture(["git", "remote", "add", "origin", "git@github.com:leandroclf/lf-openalex-enrichment-mvp.git"], repo_dir)

        issue = agentos.DeliveryBoardIssue(
            section="AUTHORIZED",
            issue_id="ISSUE-001",
            title="MVP de Enrichment B2B com OpenAlex",
            execution_mode="AUTO",
            owner="builder-repo",
            workflow="build-mvp",
            priority="high",
            repo="https://github.com/leandroclf/lf-openalex-enrichment-mvp",
        )
        root_task = agentos.build_issue_task(issue, workspace_root=self.workspace_root, allowed_agents=["gemini"])
        agentos.enqueue_task(self.conn, root_task)
        agentos.Supervisor(safe_mode=False).cycle(self.conn)

        bridge_dir = Path(self.temp_dir.name) / "handoffs"
        result = agentos.export_delivery_handoff(self.conn, workspace_root=self.workspace_root, bridge_dir=bridge_dir)
        self.assertEqual(result["status"], "ready")
        request = json.loads((bridge_dir / "delivery-execution-request.json").read_text(encoding="utf-8"))
        self.assertEqual(request["task"]["issueId"], "ISSUE-001")
        self.assertTrue(request["repoReadiness"]["canExecuteMutations"])

    def test_export_delivery_handoff_marks_dirty_repo(self) -> None:
        repo_dir = self.workspace_root / "projects" / "lf-openalex-enrichment-mvp"
        repo_dir.mkdir(parents=True)
        agentos.run_capture(["git", "init", "-b", "main"], repo_dir)
        agentos.run_capture(["git", "config", "user.name", "Test"], repo_dir)
        agentos.run_capture(["git", "config", "user.email", "test@example.com"], repo_dir)
        (repo_dir / "README.md").write_text("demo\n", encoding="utf-8")
        agentos.run_capture(["git", "add", "README.md"], repo_dir)
        agentos.run_capture(["git", "commit", "-m", "init"], repo_dir)
        (repo_dir / "dirty.txt").write_text("dirty\n", encoding="utf-8")

        issue = agentos.DeliveryBoardIssue(
            section="AUTHORIZED",
            issue_id="ISSUE-001",
            title="MVP de Enrichment B2B com OpenAlex",
            execution_mode="AUTO",
            owner="builder-repo",
            workflow="build-mvp",
            priority="high",
            repo="https://github.com/leandroclf/lf-openalex-enrichment-mvp",
        )
        root_task = agentos.build_issue_task(issue, workspace_root=self.workspace_root, allowed_agents=["gemini"])
        agentos.enqueue_task(self.conn, root_task)
        agentos.Supervisor(safe_mode=False).cycle(self.conn)

        bridge_dir = Path(self.temp_dir.name) / "handoffs"
        result = agentos.export_delivery_handoff(self.conn, workspace_root=self.workspace_root, bridge_dir=bridge_dir)
        self.assertEqual(result["status"], "ready")
        self.assertFalse(result["repoCanExecuteMutations"])
        self.assertEqual(result["repoDenyReason"], "repo_dirty")


if __name__ == "__main__":
    unittest.main()
