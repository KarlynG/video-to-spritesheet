"""Exercise the real SDK client/server stdio handshake and tool calls."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from create_demo import create_video


@unittest.skipUnless(importlib.util.find_spec("mcp") and shutil.which("ffmpeg"), "Install .[mcp] and FFmpeg")
class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_tools_conversion_and_root_boundary(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            create_video(root / "robot.mp4")
            params = StdioServerParameters(command=sys.executable,
                                           args=["-m", "video_to_spritesheet.mcp_server"],
                                           env={**os.environ, "SPRITESHEET_ROOT": temp})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listing = await session.list_tools()
                    self.assertEqual({t.name for t in listing.tools}, {"inspect_video", "conversion_options", "convert_video",
                                                                     "validate_spritesheet", "preview_spritesheet"})
                    options = await session.call_tool("conversion_options", {})
                    self.assertFalse(options.isError)
                    schema = json.loads(options.content[0].text)["schema"]
                    self.assertTrue({"unity", "unreal-paper2d", "phaser"}.issubset(schema["properties"]["format"]["enum"]))
                    inspect = await session.call_tool("inspect_video", {"input_path": "robot.mp4"})
                    self.assertFalse(inspect.isError)
                    result = await session.call_tool("convert_video", {"input_path": "robot.mp4", "output_directory": "output",
                                                       "preset": "legacy-green", "options": {"frame_count": 4, "columns": 2}})
                    self.assertFalse(result.isError, result)
                    self.assertEqual(json.loads(result.content[0].text)["frame_count"], 4)
                    valid = await session.call_tool("validate_spritesheet", {"manifest_path": "output/manifest.json"})
                    self.assertFalse(valid.isError)
                    preview = await session.call_tool("preview_spritesheet", {"image_path": "output/preview.png"})
                    self.assertFalse(preview.isError)
                    self.assertEqual(preview.content[0].type, "image")
                    for engine in ("unity", "unreal-paper2d"):
                        result = await session.call_tool("convert_video", {
                            "input_path": "robot.mp4", "output_directory": engine,
                            "options": {"frame_count": 2, "format": engine, "preview": False}})
                        self.assertFalse(result.isError, result)
                        data = json.loads(result.content[0].text)
                        self.assertEqual(data["engine_export"]["engine"], engine)
                        valid = await session.call_tool("validate_spritesheet", {"manifest_path": engine + "/manifest.json"})
                        self.assertFalse(valid.isError, valid)
                    outside = await session.call_tool("inspect_video", {"input_path": "../outside.mp4"})
                    self.assertTrue(outside.isError)
                    unknown = await session.call_tool("convert_video", {"input_path": "robot.mp4", "output_directory": "bad",
                                                                       "options": {"made_up": True}})
                    self.assertTrue(unknown.isError)


if __name__ == "__main__":
    unittest.main()
