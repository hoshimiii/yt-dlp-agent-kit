from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from yt_agent.policy import Policy, Rejected, dumps, envelope
from yt_agent.service import Service, run_worker

URL = "https://youtu.be/BaW_jenozKc"


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.policy = Policy(state_root=str(root / "state"), download_root=str(root / "downloads"), allow_downloads=True)
        self.requests = []

        def runner(policy, request, job):
            self.requests.append(request)
            if request["operation"] == "download":
                (job / "media.mp4").write_bytes(b"media-fixture")
                return {"filename": "media.mp4", "bytes": 13}
            return envelope({"title": "fixture"})

        self.service = Service(self.policy, runner)

    def plan(self):
        return self.service.plan_download(URL)["plan_id"]

    def test_inspect_and_subtitle_contracts(self):
        self.assertEqual(self.service.inspect(URL)["trust"], "untrusted_external_data")
        self.service.subtitles(URL, "en")
        self.assertEqual(self.requests[-1]["language"], "en")
        self.assertEqual(list(Path(self.policy.state_root).iterdir()), [])

    def test_plan_is_offline_and_requires_local_approval(self):
        identifier = self.plan()
        self.assertEqual(self.requests, [])
        with self.assertRaises(Rejected):
            self.service.download(identifier)
        self.assertEqual(self.requests, [])

    def test_download_disabled_even_when_plan_approved(self):
        identifier = self.plan()
        self.service.approve(identifier)
        disabled = Service(replace(self.policy, allow_downloads=False), self.service.runner)
        with self.assertRaises(Rejected):
            disabled.download(identifier)
        with self.assertRaises(Rejected):
            disabled.approve(identifier)

    def test_approval_single_use_and_fixed_destination(self):
        identifier = self.plan()
        self.service.approve(identifier)
        result = self.service.download(identifier)
        self.assertEqual(Path(result["path"]).read_bytes(), b"media-fixture")
        self.assertEqual(Path(result["path"]).parent, Path(self.policy.download_root) / identifier)
        for action in [self.service.download, self.service.approve]:
            with self.assertRaises(Rejected):
                action(identifier)
        self.assertEqual(len(self.requests), 1)

    def test_cli_approval_is_idempotent_and_consumes_once(self):
        identifier = self.plan()
        config = Path(self.temp.name) / "config.json"
        config.write_text(dumps(self.policy.__dict__), encoding="utf-8")
        env = os.environ.copy()
        env["YTAGENT_CONFIG"] = str(config)
        command = [sys.executable, "-I", "-m", "yt_agent.cli", "approve", identifier]
        plan_path = Path(self.policy.state_root) / identifier / "plan.json"
        plan_bytes = plan_path.read_bytes()
        first = subprocess.run(command, capture_output=True, text=True, timeout=10, env=env)
        approval = Path(self.policy.state_root) / identifier / "approved.json"
        original_bytes = approval.read_bytes()
        second = subprocess.run(command, capture_output=True, text=True, timeout=10, env=env)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(first.stderr, "")
        self.assertEqual(second.stderr, "")
        first_result = json.loads(first.stdout)
        second_result = json.loads(second.stdout)
        self.assertEqual(first_result, second_result)
        self.assertEqual(first_result["result"], {"approved": identifier, "expires_at": self.service.read_plan(identifier)[1]["expires_at"]})
        self.assertEqual(approval.read_bytes(), original_bytes)
        self.assertEqual(plan_path.read_bytes(), plan_bytes)
        self.service.download(identifier)
        with self.assertRaises(Rejected):
            self.service.download(identifier)
        self.assertEqual([request["operation"] for request in self.requests], ["download"])

    def test_matching_existing_approval_is_read_only(self):
        identifier = self.plan()
        expected = self.service.approve(identifier)
        approval = Path(self.policy.state_root) / identifier / "approved.json"
        original_bytes = approval.read_bytes()
        approval.chmod(0o400)
        try:
            with patch("yt_agent.service.write_new", side_effect=AssertionError("existing approval must not be rewritten")):
                self.assertEqual(self.service.approve(identifier), expected)
        finally:
            approval.chmod(0o600)
        self.assertEqual(approval.read_bytes(), original_bytes)

    def test_malformed_or_mismatched_approval_is_not_overwritten(self):
        for record in [b"{", dumps({"sha256": "0" * 64}).encode(),
                       dumps({"sha256": "0" * 64, "extra": True}).encode()]:
            with self.subTest(record=record):
                identifier = self.plan()
                self.service.approve(identifier)
                approval = Path(self.policy.state_root) / identifier / "approved.json"
                approval.write_bytes(record)
                with self.assertRaises(Rejected):
                    self.service.approve(identifier)
                self.assertEqual(approval.read_bytes(), record)
                self.assertFalse((approval.parent / "consumed.json").exists())

    def test_approval_expiring_after_plan_lock_keeps_state_intact(self):
        identifier = self.plan()
        plan_dir = Path(self.policy.state_root) / identifier
        expires_at = json.loads((plan_dir / "plan.json").read_text())["expires_at"]
        with patch("yt_agent.service.time.time", side_effect=[expires_at - 1, expires_at]):
            with self.assertRaisesRegex(Rejected, "expired"):
                self.service.approve(identifier)
        self.assertFalse((plan_dir / "approved.json").exists())
        self.assertFalse((plan_dir / "consumed.json").exists())
        self.assertFalse((plan_dir / "busy").exists())
        self.assertEqual(self.requests, [])

    def test_modified_plan_invalidates_approval(self):
        identifier = self.plan()
        self.service.approve(identifier)
        path = Path(self.policy.state_root) / identifier / "plan.json"
        plan = json.loads(path.read_text())
        plan["kind"] = "audio"
        path.write_text(dumps(plan))
        with self.assertRaises(Rejected):
            self.service.download(identifier)

    def test_policy_change_invalidates_plan(self):
        identifier = self.plan()
        changed = Service(replace(self.policy, max_media_bytes=1024), self.service.runner)
        with self.assertRaises(Rejected):
            changed.approve(identifier)

    def test_expired_and_traversal_plans(self):
        identifier = self.plan()
        with patch("yt_agent.service.time.time", return_value=9999999999):
            with self.assertRaises(Rejected):
                self.service.approve(identifier)
        for value in ["../x", "A" * 32, "0" * 33, [], None]:
            with self.subTest(value=value), self.assertRaises(Rejected):
                self.service.download(value)

    def test_global_busy_preserves_approval_for_same_plan_retry(self):
        identifier = self.plan()
        self.service.approve(identifier)
        plan_dir = Path(self.policy.state_root) / identifier
        with self.service.work():
            with self.assertRaisesRegex(Rejected, "Operation not started, wait until idle; crash recovery may require operator"):
                self.service.download(identifier)
            self.assertTrue((plan_dir / "approved.json").exists())
            self.assertFalse((plan_dir / "consumed.json").exists())
            self.assertEqual(self.requests, [])
            self.assertFalse(Path(self.policy.download_root).exists())
        result = self.service.download(identifier)
        self.assertEqual(Path(result["path"]).read_bytes(), b"media-fixture")
        self.assertEqual([request["operation"] for request in self.requests], ["download"])
        with self.assertRaises(Rejected):
            self.service.download(identifier)
        self.assertEqual(len(self.requests), 1)

    def test_plan_lock_and_global_lock_have_distinct_messages(self):
        identifier = self.plan()
        self.service.approve(identifier)
        plan_dir = Path(self.policy.state_root) / identifier
        with self.service.locked(plan_dir):
            with self.assertRaisesRegex(Rejected, "Plan is busy or requires crash recovery"):
                self.service.download(identifier)
        with self.service.work():
            with self.assertRaisesRegex(Rejected, "Operation not started, wait until idle"):
                self.service.download(identifier)

    def test_plan_expiring_during_admission_retains_approval(self):
        identifier = self.plan()
        self.service.approve(identifier)
        plan_dir = Path(self.policy.state_root) / identifier
        expires_at = json.loads((plan_dir / "plan.json").read_text())["expires_at"]
        with patch("yt_agent.service.time.time", side_effect=[expires_at - 1, expires_at]):
            with self.assertRaisesRegex(Rejected, "Plan expired before execution"):
                self.service.download(identifier)
        self.assertTrue((plan_dir / "approved.json").exists())
        self.assertFalse((plan_dir / "consumed.json").exists())
        self.assertFalse((plan_dir / "busy").exists())
        self.assertFalse(Path(self.policy.download_root).exists())
        self.assertEqual(self.requests, [])
        self.assertEqual(list(Path(self.policy.state_root).glob("job-*")), [])

    def test_failed_download_consumes_approval(self):
        identifier = self.plan()
        self.service.approve(identifier)
        def failing(*args):
            raise Rejected("fixture failure")
        service = Service(self.policy, failing)
        with self.assertRaises(Rejected):
            service.download(identifier)
        with self.assertRaises(Rejected):
            self.service.download(identifier)

    def test_unknown_args_and_approval_tool_rejected(self):
        for request in [{"tool": "approve", "arguments": {"identifier": "0" * 32}},
                        {"tool": "video_info", "arguments": {"url": URL, "exec": "evil"}},
                        {"tool": "video_download", "arguments": {"identifier": "0" * 32, "confirmed": True}},
                        {"tool": "video_info", "arguments": {}},
                        {"tool": "video_info", "arguments": [], "config": {}}, {}]:
            with self.subTest(request=request), self.assertRaises(Rejected):
                self.service.call(request)

    def test_filename_from_worker_cannot_escape(self):
        identifier = self.plan()
        self.service.approve(identifier)
        service = Service(self.policy, lambda *args: {"filename": "../../stolen", "bytes": 1})
        with self.assertRaises(Rejected):
            service.download(identifier)
        self.assertFalse(Path(self.policy.download_root).joinpath(identifier).exists())

    def test_concurrent_consumers_only_one_download(self):
        identifier = self.plan()
        self.service.approve(identifier)
        def consume(_):
            try:
                return self.service.download(identifier)
            except Rejected:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(consume, range(4)))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(len(self.requests), 1)

    def test_cancelled_worker_is_reaped(self):
        event = threading.Event()
        event.set()
        with self.service.work() as job, self.assertRaises(Rejected):
            run_worker(self.policy, {"operation": "inspect", "url": URL}, job, cancel_event=event)

    def test_running_worker_cancelled_and_waited(self):
        original_popen = subprocess.Popen
        captured = []
        ready = threading.Event()
        cancelled = threading.Event()
        def hung_worker(command, **kwargs):
            proc = original_popen([sys.executable, "-I", "-c",
                "import sys,time; sys.stdout.write('ready'); sys.stdout.flush(); time.sleep(30)"], **kwargs)
            captured.append(proc)
            ready.set()
            return proc
        with self.service.work() as job, patch("yt_agent.service.subprocess.Popen", side_effect=hung_worker):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(run_worker, self.policy, {"operation": "inspect", "url": URL}, job, cancelled)
                self.assertTrue(ready.wait(3))
                self.assertIsNone(captured[0].poll())
                cancelled.set()
                with self.assertRaises(Rejected):
                    future.result(timeout=5)
        self.assertIsNotNone(captured[0].poll())

    def test_global_worker_slot_does_not_multiply_resource_limits(self):
        with self.service.work():
            with self.assertRaises(Rejected):
                with Service(self.policy).work():
                    self.fail("Concurrent worker admitted")

    def test_cli_show_plan_reports_validated_policy_without_writing_state(self):
        root = Path(self.temp.name)
        for enabled, limit in [(False, 1024 * 1024), (True, 2 * 1024 * 1024)]:
            with self.subTest(enabled=enabled, limit=limit):
                state = root / f"show-state-{enabled}"
                output = root / f"show-output-{enabled}"
                policy = replace(self.policy, state_root=str(state), download_root=str(output),
                                 allow_downloads=enabled, max_media_bytes=limit)
                config = root / f"show-config-{enabled}.json"
                config.write_text(dumps(policy.__dict__), encoding="utf-8")
                env = {**os.environ, "YTAGENT_CONFIG": str(config)}

                def cli(*args, input_text=None):
                    return subprocess.run([sys.executable, "-I", "-m", "yt_agent.cli", *args],
                                          input=input_text, capture_output=True, text=True, timeout=10, env=env)

                request = dumps({"tool": "video_plan_download", "arguments": {"url": URL}})
                created = cli("call", input_text=request)
                self.assertEqual(created.returncode, 0, created.stderr)
                created_result = json.loads(created.stdout)["result"]
                self.assertEqual(created_result["max_bytes"], limit)
                self.assertEqual(created_result["downloads_enabled"], enabled)
                identifier = created_result["plan_id"]
                plan_path = state / identifier / "plan.json"
                plan_bytes = plan_path.read_bytes()
                expiry = json.loads(plan_bytes)["expires_at"]
                approval = plan_path.parent / "approved.json"
                self.assertFalse(approval.exists())

                shown = cli("show-plan", identifier)
                self.assertEqual(shown.returncode, 0, shown.stderr)
                shown_result = json.loads(shown.stdout)["result"]
                self.assertEqual(shown_result, {
                    **{key: created_result[key] for key in ("plan_id", "url", "kind", "expires_at", "policy")},
                    "max_bytes": limit, "downloads_enabled": enabled,
                })
                self.assertEqual(shown_result["expires_at"], expiry)
                self.assertEqual(plan_path.read_bytes(), plan_bytes)
                self.assertFalse(approval.exists())
                self.assertFalse((plan_path.parent / "consumed.json").exists())
                self.assertFalse((plan_path.parent / "busy").exists())
                self.assertFalse(output.exists())
                self.assertEqual(list(state.glob("job-*")), [])

                if enabled:
                    denied = cli("call", input_text=dumps({
                        "tool": "video_download", "arguments": {"identifier": identifier}}))
                    self.assertEqual(denied.returncode, 1)
                    self.assertIn("approval", json.loads(denied.stdout)["error"].lower())
                    self.assertFalse(approval.exists())
                    self.assertFalse((plan_path.parent / "consumed.json").exists())
                    self.assertFalse(output.exists())

    def test_cli_show_plan_rejects_expired_policy_changed_and_malformed_plans(self):
        root = Path(self.temp.name)

        def create_plan(name, policy):
            config = root / f"{name}.json"
            config.write_text(dumps(policy.__dict__), encoding="utf-8")
            env = {**os.environ, "YTAGENT_CONFIG": str(config)}
            request = dumps({"tool": "video_plan_download", "arguments": {"url": URL}})
            planned = subprocess.run([sys.executable, "-I", "-m", "yt_agent.cli", "call"],
                                     input=request, capture_output=True, text=True, timeout=10, env=env)
            self.assertEqual(planned.returncode, 0, planned.stderr)
            identifier = json.loads(planned.stdout)["result"]["plan_id"]
            return config, env, identifier, Path(policy.state_root) / identifier / "plan.json"

        for case in ("expired", "malformed", "extra_field", "policy_changed"):
            with self.subTest(case=case):
                state = root / f"invalid-state-{case}"
                output = root / f"invalid-output-{case}"
                policy = replace(self.policy, state_root=str(state), download_root=str(output), allow_downloads=False)
                config, env, identifier, plan_path = create_plan(f"invalid-config-{case}", policy)
                original = plan_path.read_bytes()
                if case == "expired":
                    plan = json.loads(original)
                    plan["expires_at"] = 1
                    plan_path.write_text(dumps(plan), encoding="utf-8")
                elif case == "malformed":
                    plan_path.write_bytes(b"{")
                elif case == "extra_field":
                    plan = json.loads(original)
                    plan["extra"] = "ignored"
                    plan_path.write_text(dumps(plan), encoding="utf-8")
                else:
                    changed = replace(policy, max_media_bytes=policy.max_media_bytes + 1024)
                    config.write_text(dumps(changed.__dict__), encoding="utf-8")
                before_show = plan_path.read_bytes()
                shown = subprocess.run([sys.executable, "-I", "-m", "yt_agent.cli", "show-plan", identifier],
                                       capture_output=True, text=True, timeout=10, env=env)
                self.assertEqual(shown.returncode, 1)
                response = json.loads(shown.stdout)
                self.assertFalse(response["ok"])
                self.assertEqual(plan_path.read_bytes(), before_show)
                self.assertNotIn("max_bytes", response)
                self.assertNotIn("downloads_enabled", response)
                self.assertFalse((plan_path.parent / "approved.json").exists())
                self.assertFalse((plan_path.parent / "busy").exists())
                self.assertFalse(output.exists())

    def test_cli_missing_config_is_controlled_and_corrected_config_plans_offline(self):
        root = Path(self.temp.name)
        config = root / "missing-config-marker.json"
        request = dumps({"tool": "video_plan_download", "arguments": {"url": URL}})
        env = os.environ.copy()
        env["YTAGENT_CONFIG"] = str(config)
        command = [sys.executable, "-I", "-m", "yt_agent.cli", "call"]
        failed = subprocess.run(command, input=request, capture_output=True, text=True, timeout=10, env=env)
        self.assertEqual(failed.returncode, 1)
        self.assertEqual(failed.stderr, "")
        response = json.loads(failed.stdout)
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"], "Configured policy file was not found; ask the operator to check YTAGENT_CONFIG/configPath")
        self.assertNotIn("missing-config-marker", failed.stdout + failed.stderr)
        self.assertNotIn("FileNotFoundError", failed.stdout + failed.stderr)
        self.assertFalse(Path(self.policy.state_root).exists())
        self.assertFalse(Path(self.policy.download_root).exists())

        config.write_text(dumps(self.policy.__dict__), encoding="utf-8")
        planned = subprocess.run(command, input=request, capture_output=True, text=True, timeout=10, env=env)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        result = json.loads(planned.stdout)["result"]
        self.assertTrue(result["requires_local_approval"])
        self.assertTrue((Path(self.policy.state_root) / result["plan_id"] / "plan.json").is_file())
        self.assertFalse(Path(self.policy.download_root).exists())
        self.assertEqual(list(Path(self.policy.state_root).glob("job-*")), [])

    def test_cli_rejects_injected_request_without_network(self):
        proc = subprocess.run([sys.executable, "-I", "-m", "yt_agent.cli", "call"],
                              input=dumps({"tool": "video_info", "arguments": {"url": "file:///etc/passwd"}}),
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(json.loads(proc.stdout)["ok"])
        self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
