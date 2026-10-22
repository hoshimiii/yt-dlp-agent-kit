"""Keep package, lockfiles, runtime and client manifests on one release version."""

from importlib.metadata import version
import json
from pathlib import Path
import tomllib
import unittest

from yt_agent import __version__


class VersionTests(unittest.TestCase):
    def test_release_versions_match(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(version("yt-dlp-agent-kit"), __version__)
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["version"], __version__)
        lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
        package = next(item for item in lock["package"] if item["name"] == "yt-dlp-agent-kit")
        self.assertEqual(package["version"], __version__)
        for name in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json",
                     "adapters/dsh/package.json", "adapters/dsh/package-lock.json"):
            with self.subTest(manifest=name):
                metadata = json.loads((root / name).read_text(encoding="utf-8"))
                self.assertEqual(metadata["version"], __version__)
                if "packages" in metadata:
                    self.assertEqual(metadata["packages"][""]["version"], __version__)
