"""One short-lived yt-dlp operation. This module is not a public tool."""

from dataclasses import asdict
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

from .policy import Policy, Rejected, dumps, envelope, finite_number, language, public_ip, remote_url, text_data, video_url


class QuietLogger:
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass


def install_guards(max_network_bytes=4 * 1024 * 1024):
    """Guards are process-local: never monkeypatch the agent/MCP host process."""
    original_socket = socket.socket
    original_open = urllib.request.OpenerDirector.open
    from yt_dlp.networking._urllib import HTTPHandler
    remaining = max_network_bytes

    def bound_response(response):
        original_read = response.read

        def read(size=-1):
            nonlocal remaining
            requested = remaining + 1 if size is None or size < 0 else min(size, remaining + 1)
            value = original_read(requested)
            remaining -= len(value)
            if remaining < 0:
                raise Rejected("Network response budget exceeded")
            return value

        def readinto(buffer):
            value = read(len(buffer))
            buffer[:len(value)] = value
            return len(value)

        # Preserve HTTPResponse/addinfourl identity for yt-dlp's HTTP-error adapter.
        response.read = read
        response.readinto = readinto
        return response

    class PublicSocket(original_socket):
        def connect(self, address):
            if self.family not in (socket.AF_INET, socket.AF_INET6):
                raise Rejected("Only public internet connections are permitted")
            public_ip(address[0])
            if address[1] != 443:
                raise Rejected("Only TLS port 443 is permitted")
            return super().connect(address)

        def connect_ex(self, address):
            self.connect(address)
            return 0

    def https_open(opener, fullurl, *args, **kwargs):
        remote_url(fullurl if isinstance(fullurl, str) else fullurl.full_url)
        if not isinstance(fullurl, str):
            fullurl.add_header("Accept-Encoding", "identity")
        return original_open(opener, fullurl, *args, **kwargs)

    def bounded_response(handler, request, response):
        # Run before HTTPErrorProcessor and yt-dlp's eager decompression.
        if response.headers.get("Content-Encoding", "identity").lower().strip() not in ("", "identity"):
            response.close()
            raise Rejected("Compressed HTTP responses are disabled")
        return bound_response(response)

    def deny_process(*args, **kwargs):
        raise Rejected("External executables are disabled in the worker")

    socket.socket = PublicSocket
    urllib.request.OpenerDirector.open = https_open
    HTTPHandler.http_response = HTTPHandler.https_response = bounded_response
    subprocess.Popen = deny_process
    os.system = deny_process


def yt_options(policy, job, operation):
    def bound_progress(progress):
        if (progress.get("downloaded_bytes") or 0) > policy.max_media_bytes:
            raise Rejected("Media size limit exceeded")

    return {
        "quiet": True, "no_warnings": True, "logger": QuietLogger(), "noprogress": True,
        "noplaylist": True,
        "cachedir": False, "proxy": "", "socket_timeout": 10,
        "retries": 1, "fragment_retries": 0, "extractor_retries": 0,
        "file_access_retries": 0, "concurrent_fragment_downloads": 1,
        "js_runtimes": {}, "remote_components": [], "postprocessors": [], "fixup": "never",
        "overwrites": False, "continuedl": False, "nopart": False,
        "writeinfojson": False, "writethumbnail": False, "writedescription": False,
        "outtmpl": str(Path(job) / "media.%(ext)s"), "restrictfilenames": True,
        "max_filesize": policy.max_media_bytes, "progress_hooks": [bound_progress],
        "format": "best[protocol=https][vcodec!=?none][acodec!=?none][height<=?720]",
        "skip_download": operation != "download", "ignoreerrors": False,
    }


def run(request):
    # Set before importing yt-dlp: its plugin loader also runs during YoutubeDL construction.
    os.environ["YTDLP_NO_PLUGINS"] = "1"
    import yt_dlp
    from yt_dlp.networking._urllib import UrllibRH

    policy = Policy(**request["policy"])
    url = video_url(request["url"], policy)
    op = request["operation"]
    job = Path(request["job"])
    install_guards(4 * 1024 * 1024 + (policy.max_media_bytes if op == "download" else 0))

    class SafeYDL(yt_dlp.YoutubeDL):
        def build_request_director(self, handlers, preferences=None):
            return super().build_request_director([UrllibRH], preferences)

    options = yt_options(policy, job, op)
    if op == "download" and request["kind"] == "audio":
        # YoutubeDL compiles the format selector once, during construction.
        options["format"] = "bestaudio[protocol=https]/best[protocol=https]"
    with SafeYDL(options) as ydl:
        info = ydl.extract_info(url, download=False, process=False)
        if not isinstance(info, dict) or info.get("_type", "video") != "video":
            raise Rejected("Only a single video result is accepted")
        if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming", "post_live"):
            raise Rejected("Live or unfinished streams are not accepted")
        if op == "inspect":
            subs = set((info.get("subtitles") or {})) | set((info.get("automatic_captions") or {}))
            return envelope({
                "title": text_data(info.get("title"), 500),
                "description": text_data(info.get("description"), min(4000, policy.max_text_chars)),
                "uploader": text_data(info.get("uploader"), 200),
                "duration": finite_number(info.get("duration")),
                "subtitle_languages": [text_data(s, 30) for s in sorted(subs)[:50]],
                "source_url": url,
            })
        if op == "subtitles":
            lang = language(request["language"])
            tracks = (info.get("subtitles") or {}).get(lang) or (info.get("automatic_captions") or {}).get(lang)
            track = next((t for t in (tracks or []) if t.get("ext") in ("vtt", "srt")), None)
            if not track:
                raise Rejected("No VTT/SRT subtitle track for the requested language")
            remote_url(track["url"])
            with ydl.urlopen(track["url"]) as response:
                raw = response.read(policy.max_subtitle_bytes + 1)
            if len(raw) > policy.max_subtitle_bytes:
                raise Rejected("Subtitle byte limit exceeded")
            text = raw.decode("utf-8-sig", errors="replace")
            return envelope({"language": lang, "format": track["ext"],
                             "text": text_data(text, policy.max_text_chars),
                             "truncated": len(text) > policy.max_text_chars, "source_url": url})
        if op != "download":
            raise Rejected("Unknown worker operation")
        # Direct HTTPS single-file formats avoid FFmpeg, manifests and subprocesses.
        selected = ydl.process_ie_result(info, download=False)
        if selected.get("requested_formats") or selected.get("protocol") != "https":
            raise Rejected("A single direct HTTPS format is required")
        ext = selected.get("ext")
        if ext not in ("mp4", "webm", "m4a", "opus", "ogg", "mp3", "aac", "wav", "flac"):
            raise Rejected("Unsupported media container")
        remote_url(selected["url"])
        size = selected.get("filesize") or selected.get("filesize_approx")
        if size and size > policy.max_media_bytes:
            raise Rejected("Media size limit exceeded")
        ydl.params["skip_download"] = False
        ydl.process_info(selected)
        path = job / f"media.{ext}"
        if not path.is_file() or path.stat().st_size > policy.max_media_bytes:
            raise Rejected("Download did not produce a bounded media file")
        return {"filename": path.name, "bytes": path.stat().st_size}


def main():
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise Rejected("Worker request too large")
        request = json.loads(raw)
        if sys.platform.startswith("linux"):
            import ctypes
            import resource
            import signal
            if ctypes.CDLL(None).prctl(1, signal.SIGKILL) != 0:
                raise Rejected("Cannot establish worker parent lifecycle")
            if os.getppid() != request["parent_pid"]:
                raise Rejected("Worker parent is gone")
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            max_file = request["policy"]["max_media_bytes"] + 65536
            resource.setrlimit(resource.RLIMIT_FSIZE, (max_file, max_file))
        result = run(request)
        sys.stdout.write(dumps({"ok": True, "result": result}))
    except Exception as exc:
        # Upstream errors may contain signed URLs, local paths or remote instructions.
        message = str(exc) if isinstance(exc, Rejected) else "Upstream operation failed or was blocked by policy; no automatic policy relaxation."
        sys.stdout.write(dumps({"ok": False, "error": message}))
        sys.exit(1)


if __name__ == "__main__":
    main()
