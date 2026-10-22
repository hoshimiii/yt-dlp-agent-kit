"""Shared service: bounded subprocesses, fixed paths and one-use approvals."""

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

from .policy import Policy, Rejected, dumps, language, read_json, safe_path, video_url


def plan_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise Rejected("Invalid plan identifier")
    return value


def write_new(path, value):
    safe_path(path)
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(dumps(value))


def windows_job(proc):
    if sys.platform != "win32":
        return None
    import win32job
    job = win32job.CreateJobObject(None, "")
    info = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
    info["BasicLimitInformation"]["LimitFlags"] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
    info["ProcessMemoryLimit"] = 512 * 1024 * 1024
    win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, info)
    win32job.AssignProcessToJobObject(job, proc._handle)
    return job


def run_worker(policy, request, directory, cancel_event=None):
    request = {**request, "policy": asdict(policy), "job": str(directory), "parent_pid": os.getpid()}
    # Pass only platform runtime variables; never forward tokens, PYTHONPATH or proxies.
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL"}}
    env["YTDLP_NO_PLUGINS"] = "1"
    deadline = time.monotonic() + policy.timeout_seconds
    worker_job = None
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen([sys.executable, "-I", "-m", "yt_agent.worker"],
                                stdin=subprocess.PIPE, stdout=output, stderr=errors,
                                cwd=directory, env=env,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            worker_job = windows_job(proc)
            proc.stdin.write(dumps(request).encode())
            proc.stdin.close()
            while proc.poll() is None:
                if cancel_event is not None and cancel_event.is_set():
                    raise Rejected("Operation cancelled; worker stopped")
                if time.monotonic() > deadline:
                    raise Rejected("Operation timed out; worker stopped")
                if os.fstat(output.fileno()).st_size > 512 * 1024 or os.fstat(errors.fileno()).st_size > 65536:
                    raise Rejected("Worker output limit exceeded")
                total = sum(p.stat().st_size for p in directory.iterdir() if p.is_file())
                if total > policy.max_media_bytes + 65536:
                    raise Rejected("Job disk limit exceeded")
                time.sleep(0.05)
            output.seek(0)
            raw = output.read(512 * 1024 + 1)
            if len(raw) > 512 * 1024:
                raise Rejected("Worker output limit exceeded")
            try:
                value = json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                raise Rejected("Invalid worker response") from exc
            if proc.returncode != 0 or value.get("ok") is not True:
                raise Rejected(value.get("error", "Upstream operation failed or was blocked by policy"))
            return value["result"]
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            if worker_job is not None:
                worker_job.Close()


class Service:
    def __init__(self, policy=None, runner=run_worker):
        self.policy = policy or Policy.load()
        self.runner = runner

    def root(self):
        root = safe_path(self.policy.state_root)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        return root

    @contextmanager
    def work(self):
        # One worker per shared state root across MCP, DSH and CLI processes.
        root = self.root()
        with self.locked(root, "Operation not started, wait until idle; crash recovery may require operator"), tempfile.TemporaryDirectory(prefix="job-", dir=root) as name:
            yield Path(name)

    def inspect(self, url):
        url = video_url(url, self.policy)
        with self.work() as job:
            return self.runner(self.policy, {"operation": "inspect", "url": url}, job)

    def subtitles(self, url, lang="en"):
        url, lang = video_url(url, self.policy), language(lang)
        with self.work() as job:
            return self.runner(self.policy, {"operation": "subtitles", "url": url, "language": lang}, job)

    def plan_download(self, url, kind="video"):
        url = video_url(url, self.policy)
        if kind not in ("video", "audio"):
            raise Rejected("kind must be video or audio")
        identifier = uuid.uuid4().hex
        plan = {"plan_id": identifier, "url": url, "kind": kind,
                "expires_at": int(time.time()) + 900, "policy": self.policy.fingerprint()}
        directory = self.root() / identifier
        directory.mkdir(mode=0o700)
        write_new(directory / "plan.json", plan)
        return {**plan, "requires_local_approval": True, "downloads_enabled": self.policy.allow_downloads,
                "max_bytes": self.policy.max_media_bytes}

    def read_plan(self, identifier):
        identifier = plan_id(identifier)
        directory = safe_path(self.root() / identifier)
        if not directory.is_dir():
            raise Rejected("Plan does not exist")
        plan = read_json(directory / "plan.json")
        if (not isinstance(plan, dict) or set(plan) != {"plan_id", "url", "kind", "expires_at", "policy"}
                or plan.get("plan_id") != identifier or type(plan.get("expires_at")) is not int
                or plan["expires_at"] <= time.time() or plan.get("policy") != self.policy.fingerprint()
                or plan.get("kind") not in ("video", "audio")):
            raise Rejected("Plan is invalid, expired or belongs to a different policy")
        if video_url(plan["url"], self.policy) != plan["url"]:
            raise Rejected("Plan URL is not canonical")
        digest = hashlib.sha256(dumps(plan).encode()).hexdigest()
        return directory, plan, digest

    @contextmanager
    def locked(self, directory, busy_message="Plan is busy or requires crash recovery; do not retry concurrently"):
        lock = directory / "busy"
        safe_path(lock)
        try:
            stream = lock.open("x")
        except FileExistsError as exc:
            raise Rejected(busy_message) from exc
        try:
            with stream:
                stream.write(dumps({"pid": os.getpid()}))
                stream.flush()
                yield
        finally:
            lock.unlink()

    def approve(self, identifier):
        if not self.policy.allow_downloads:
            raise Rejected("Downloads are disabled by operator policy")
        directory, plan, digest = self.read_plan(identifier)
        with self.locked(directory):
            if (directory / "consumed.json").exists():
                raise Rejected("This plan was already consumed; create a new plan")
            write_new(directory / "approved.json", {"sha256": digest})
        return {"approved": plan["plan_id"], "expires_at": plan["expires_at"]}

    def download(self, identifier):
        if not self.policy.allow_downloads:
            raise Rejected("Downloads are disabled by operator policy")
        directory, plan, digest = self.read_plan(identifier)
        with self.locked(directory):
            approval = directory / "approved.json"
            try:
                if read_json(approval) != {"sha256": digest}:
                    raise Rejected("Approval does not match the immutable plan")
            except FileNotFoundError as exc:
                raise Rejected("Plan needs local approval or has already been consumed") from exc
            consumed = safe_path(directory / "consumed.json")
            if consumed.exists():
                raise Rejected("Plan already consumed")
            with self.work() as job:
                if plan["expires_at"] <= time.time():
                    raise Rejected("Plan expired before execution; create a new plan and approval")
                approval.rename(consumed)
                # Consume before network access: failures require a fresh plan/approval.
                root = safe_path(self.policy.download_root)
                root.mkdir(parents=True, exist_ok=True, mode=0o700)
                destination = safe_path(root / plan["plan_id"])
                if destination.exists():
                    raise Rejected("Destination already exists")
                result = self.runner(self.policy, {"operation": "download", "url": plan["url"], "kind": plan["kind"]}, job)
                filename = result.get("filename", "")
                if not re.fullmatch(r"media\.(mp4|webm|m4a|opus|ogg|mp3|aac|wav|flac)", filename):
                    raise Rejected("Invalid worker media filename")
                source = safe_path(job / filename)
                if not source.is_file() or not 0 < source.stat().st_size <= self.policy.max_media_bytes:
                    raise Rejected("Missing or oversized media output")
                destination.mkdir(mode=0o700)
                try:
                    # Copy across filesystems; exclusive creation prevents replacement.
                    with source.open("rb") as inp, (destination / filename).open("xb") as out:
                        shutil.copyfileobj(inp, out, 65536)
                except BaseException:
                    # Only this call's newly created file/directory is eligible for cleanup.
                    (destination / filename).unlink(missing_ok=True)
                    destination.rmdir()
                    raise
                return {"plan_id": plan["plan_id"], "path": str(destination / filename),
                        "bytes": source.stat().st_size, "kind": plan["kind"]}

    def call(self, request):
        if not isinstance(request, dict) or set(request) != {"tool", "arguments"}:
            raise Rejected("Expected exactly tool and arguments")
        tool, args = request["tool"], request["arguments"]
        allowed = {"video_info": ({"url"}, {"url"}, self.inspect),
                   "video_subtitles": ({"url", "lang"}, {"url"}, self.subtitles),
                   "video_plan_download": ({"url", "kind"}, {"url"}, self.plan_download),
                   "video_download": ({"identifier"}, {"identifier"}, self.download)}
        if not isinstance(tool, str) or tool not in allowed:
            raise Rejected("Unknown tool")
        keys, required, function = allowed[tool]
        if not isinstance(args, dict) or set(args) - keys or required - set(args):
            raise Rejected("Unexpected or missing tool arguments")
        return function(**args)
