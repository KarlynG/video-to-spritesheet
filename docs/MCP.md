# Local MCP server

For an MCP client, install the package with the optional SDK adapter. FFmpeg must be installed as described in [installation](USAGE.md#installation).

```bash
pipx install "video-to-spritesheet[mcp]"
```

pipx adds a `video-to-spritesheet-mcp` command; point your client at its absolute path (`which video-to-spritesheet-mcp`, or `where` on Windows) with no args. If you installed into a virtual environment instead (`python -m pip install "video-to-spritesheet[mcp]"`, or `-e ".[mcp]"` from a clone), configure your MCP client to launch that environment's **absolute Python executable**:

```json
{
  "mcpServers": {
    "video-to-spritesheet": {
      "command": "/absolute/path/video-to-spritesheet/.venv/bin/python",
      "args": ["-m", "video_to_spritesheet.mcp_server"],
      "env": {"SPRITESHEET_ROOT": "/absolute/path/to/your/assets"}
    }
  }
}
```

On Windows use a path such as `C:\\tools\\video-to-spritesheet\\.venv\\Scripts\\python.exe`. On macOS/Linux use `.venv/bin/python`. This JSON shape works in clients that use the `mcpServers` configuration convention; clients with another configuration UI should use the same command, args, and environment values there.

The server uses **stdio**, runs locally, and processes local files. `SPRITESHEET_ROOT` limits accessible paths; relative paths resolve inside it. Set this variable explicitly when configuring a client. It defaults to the launch directory. This is a local integration, not a hosted HTTP service.

| Tool | Purpose |
| --- | --- |
| `inspect_video` | Input dimensions, duration, FPS, codec |
| `conversion_options` | Supported options schema, defaults, presets, formats |
| `convert_video` | Run the same converter as the CLI |
| `validate_spritesheet` | Check actual images and metadata |
| `preview_spritesheet` | Return an existing preview as an MCP image |

Example `convert_video` arguments:

```json
{
  "input_path": "character.webm",
  "output_directory": "generated/character",
  "preset": "legacy-green",
  "options": {
    "frame_count": 48,
    "frame_width": 128,
    "frame_height": 128,
    "columns": 8,
    "rows": 6,
    "format": "unity",
    "pixels_per_unit": 100,
    "pivot_x": 0.5,
    "pivot_y": 0
  }
}
```
