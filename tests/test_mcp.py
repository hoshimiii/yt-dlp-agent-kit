import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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


if __name__ == "__main__":
    unittest.main()
