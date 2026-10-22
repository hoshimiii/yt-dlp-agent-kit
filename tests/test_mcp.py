import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from yt_agent import mcp_server


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_real_client_discovery_denials_and_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.json"
            config.write_text(json.dumps({"state_root": str(root / "state"), "download_root": str(root / "downloads")}))
            params = StdioServerParameters(command=sys.executable,
                args=["-I", "-m", "yt_agent.mcp_server"], env={**os.environ, "YTAGENT_CONFIG": str(config)})
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                init = await session.initialize()
                self.assertIn("untrusted", init.instructions)
                tools = (await session.list_tools()).tools
                self.assertEqual(len(tools), 4)
                self.assertNotIn("approve", [tool.name for tool in tools])
                denied = await session.call_tool("video_info", {"url": "file:///etc/passwd"})
                self.assertTrue(denied.isError)
                extra = await session.call_tool("video_info", {"url": "https://youtu.be/BaW_jenozKc", "exec": "evil"})
                self.assertTrue(extra.isError)
                planned = await session.call_tool("video_plan_download", {"url": "https://youtu.be/BaW_jenozKc"})
                self.assertFalse(planned.isError)
                self.assertTrue(planned.structuredContent["requires_local_approval"])
                denied = await session.call_tool("video_download", {"identifier": planned.structuredContent["plan_id"]})
                self.assertTrue(denied.isError)
            self.assertFalse((root / "downloads").exists())

    async def test_stdio_missing_config_is_controlled_and_recovers_offline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "missing-config-marker.json"
            params = StdioServerParameters(command=sys.executable,
                args=["-I", "-m", "yt_agent.mcp_server"], env={**os.environ, "YTAGENT_CONFIG": str(config)})
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                self.assertEqual(len(tools), 4)
                self.assertNotIn("approve", [tool.name for tool in tools])
                failed = await session.call_tool("video_plan_download", {"url": "https://youtu.be/BaW_jenozKc"})
                self.assertTrue(failed.isError)
                message = "\n".join(item.text for item in failed.content)
                self.assertEqual(message, "Configured policy file was not found; ask the operator to check YTAGENT_CONFIG/configPath")
                self.assertNotIn("missing-config-marker", message)
                self.assertNotIn("FileNotFoundError", message)
                self.assertFalse((root / "state").exists())
                self.assertFalse((root / "downloads").exists())

                config.write_text(json.dumps({"state_root": str(root / "state"), "download_root": str(root / "downloads")}))
                planned = await session.call_tool("video_plan_download", {"url": "https://youtu.be/BaW_jenozKc"})
                self.assertFalse(planned.isError)
                self.assertTrue((root / "state" / planned.structuredContent["plan_id"] / "plan.json").is_file())
                self.assertFalse((root / "downloads").exists())

    async def test_call_tool_sanitizes_service_initialization_errors(self):
        with patch("yt_agent.mcp_server.Service", side_effect=OSError("private-marker")):
            result = await mcp_server.call_tool("video_plan_download", {"url": "https://youtu.be/BaW_jenozKc"})
        self.assertTrue(result.isError)
        message = "\n".join(item.text for item in result.content)
        self.assertEqual(message, "Local operation failed; check operator configuration")
        self.assertNotIn("private-marker", message)


if __name__ == "__main__":
    unittest.main()
