from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
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

    def test_cli_rejects_injected_request_without_network(self):
        proc = subprocess.run([sys.executable, "-I", "-m", "yt_agent.cli", "call"],
                              input=dumps({"tool": "video_info", "arguments": {"url": "file:///etc/passwd"}}),
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(json.loads(proc.stdout)["ok"])
        self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
