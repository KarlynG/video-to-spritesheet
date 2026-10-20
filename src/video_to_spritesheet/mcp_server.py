"""Optional MCP SDK adapter. Conversion logic stays in core.py."""

from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import Any

from .core import ConversionError, FORMATS, Options, PRESETS, convert, probe, validate_manifest
from .cli import summary


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP, Image
        from mcp.types import ToolAnnotations
    except ImportError as exc:
        raise ConversionError('MCP support is not installed. Run: python -m pip install ".[mcp]"') from exc

    root = Path(os.environ.get("SPRITESHEET_ROOT", ".")).expanduser().resolve()
    server = FastMCP("video-to-spritesheet", instructions=(
        "Convert local videos into verified RGBA sprite sheets. Paths are relative to the configured "
        "SPRITESHEET_ROOT. Inspect the video and options first, convert, then validate. "
        "Do not guess an engine-specific export format. No network inputs are accepted."))

    def local(path: str) -> Path:
        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root):
            raise ConversionError("Path is outside SPRITESHEET_ROOT.")
        return candidate

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def inspect_video(input_path: str) -> dict[str, Any]:
        """Inspect local video dimensions, duration, source FPS, and codec before converting."""
        return probe(local(input_path))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def conversion_options() -> dict[str, Any]:
        """List defaults, named presets, formats, and the JSON Schema for convert_video options."""
        from .schema import options_schema
        return {"defaults": asdict(Options()), "presets": PRESETS, "formats": list(FORMATS),
                "schema": options_schema()}

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False))
    def convert_video(input_path: str, output_directory: str,
                      options: dict[str, Any] | None = None, preset: str | None = None) -> dict[str, Any]:
        """Convert a local video to PNG sheets, manifest, engine exports, and previews.

        Read conversion_options for the options schema. Examples: frame_count=48,
        frame_width=128, frame_height=128, columns=8, rows=6. Choose fps OR frame_count.
        Set format to phaser, unity, or unreal-paper2d for engine-specific import files.
        Omitted background removal preserves input alpha. preset='legacy-green' removes #00B140.
        Existing files are protected unless options.overwrite=true is explicitly requested.
        """
        if preset is not None and preset not in PRESETS:
            raise ConversionError("Unknown preset: " + preset)
        settings = {**PRESETS.get(preset, {}), **(options or {})}
        return summary(convert(local(input_path), local(output_directory), Options.from_dict(settings)))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def validate_spritesheet(manifest_path: str) -> dict[str, Any]:
        """Verify sheet dimensions, RGBA mode, frame count, rectangles, and atlas JSON consistency."""
        manifest = local(manifest_path)
        # Validate asset paths before opening: validate_manifest permits only same-directory files.
        return validate_manifest(manifest)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def preview_spritesheet(image_path: str):
        """Return an existing PNG/GIF preview as an MCP image. Use preview.png to inspect transparency."""
        image = local(image_path)
        if image.suffix.lower() not in (".png", ".gif"):
            raise ConversionError("Preview must be a PNG or GIF.")
        if image.stat().st_size > 4_000_000:
            raise ConversionError("Preview exceeds 4 MB; inspect a smaller image.")
        # FastMCP supplies the protocol image encoding; never write raw data to stdout.
        return Image(path=str(image))

    return server


def main() -> None:
    try:
        create_server().run(transport="stdio")
    except ConversionError as exc:
        import sys
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
