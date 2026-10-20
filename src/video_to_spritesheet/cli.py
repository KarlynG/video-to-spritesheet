"""Machine-readable commands with conventional exit codes and helpful --help."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
import shutil
import sys

from . import __version__
from .core import ConversionError, FORMATS, Options, PRESETS, convert, probe, validate_manifest


def _size(value: str) -> tuple[int, int]:
    try:
        w, h = value.lower().split("x")
        result = int(w), int(h)
        if min(result) <= 0:
            raise ValueError
        return result
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use a positive WIDTHxHEIGHT, for example 128x128.") from exc


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Turn local videos into verified RGBA sprite sheets and JSON atlases.")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check Python, Pillow, FFmpeg, and FFprobe.")
    commands.add_parser("formats", help="List output formats and presets.")
    inspect = commands.add_parser("probe", help="Inspect a local video as JSON.")
    inspect.add_argument("input", type=Path)
    validate = commands.add_parser("validate", help="Validate a manifest and its actual sheet files.")
    validate.add_argument("manifest", type=Path)
    commands.add_parser("mcp", help="Run the optional local MCP server on stdio.")
    run = commands.add_parser("convert", help="Extract, process, and pack a video.",
                             formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    run.add_argument("input", type=Path)
    run.add_argument("--output", "-o", required=True, type=Path, help="Output directory.")
    run.add_argument("--config", type=Path, help="JSON object of conversion options.")
    run.add_argument("--preset", choices=tuple(PRESETS))
    run.add_argument("--frame-size", type=_size, help="Output cell size, WIDTHxHEIGHT.")
    for flag, dest, kind, help_text in [
        ("--fps", "fps", float, "Sample at this many frames per second (default 12)."),
        ("--frames", "frame_count", int, "Sample exactly N frames uniformly across the selected clip; replaces default FPS."),
        ("--start", "start", float, "Start time in seconds."),
        ("--end", "end", float, "Exclusive end time in seconds."),
        ("--columns", "columns", int, "Columns per sheet."),
        ("--rows", "rows", int, "Rows per sheet; overflow creates another sheet."),
        ("--padding", "padding", int, "Transparent border around each frame."),
        ("--spacing", "spacing", int, "Gap between padded cells."),
        ("--max-sheet-size", "max_sheet_size", int, "Maximum sheet width and height (default 4096)."),
        ("--max-frames", "max_frames", int, "Maximum extracted frames (default 600)."),
        ("--max-pixels", "max_pixels", int, "Decoded/resized pixel budget (default 64000000)."),
        ("--key-color", "key_color", str, "Background RGB hex; omitted preserves the background/alpha."),
        ("--similarity", "similarity", float, "Key tolerance, 0.01..1 (default 0.12)."),
        ("--blend", "blend", float, "Key edge blend, 0..1 (default 0.04)."),
        ("--timeout", "timeout", float, "FFmpeg extraction timeout in seconds (default 300)."),
        ("--pixels-per-unit", "pixels_per_unit", float, "Unity world scale (default 100 pixels per unit)."),
        ("--pivot-x", "pivot_x", float, "Normalized frame pivot X, left to right (default 0.5)."),
        ("--pivot-y", "pivot_y", float, "Normalized frame pivot Y, bottom to top (default 0.5)."),
    ]:
        run.add_argument(flag, dest=dest, type=kind, default=argparse.SUPPRESS, help=help_text)
    run.add_argument("--fit", choices=("contain", "cover", "stretch"), default=argparse.SUPPRESS)
    run.add_argument("--resample", choices=("nearest", "lanczos"), default=argparse.SUPPRESS)
    run.add_argument("--despill", choices=("green", "blue"), default=argparse.SUPPRESS)
    run.add_argument("--format", choices=FORMATS, default=argparse.SUPPRESS)
    run.add_argument("--trim", action="store_true", default=argparse.SUPPRESS,
                     help="Crop all frames to their shared alpha bounds, preserving alignment.")
    run.add_argument("--no-preview", dest="preview", action="store_false", default=argparse.SUPPRESS)
    run.add_argument("--overwrite", action="store_true", default=argparse.SUPPRESS)
    return root


def summary(result: dict) -> dict:
    value = {key: result[key] for key in ("output_directory", "manifest", "frame_count", "frame_size", "pages", "warnings")}
    if "engine_export" in result:
        value["engine_export"] = result["engine_export"]
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            from PIL import __version__ as pillow_version
            result = {"python": sys.version.split()[0], "pillow": pillow_version,
                      "ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe")}
            result["ready"] = bool(result["ffmpeg"] and result["ffprobe"])
            print(json.dumps(result, indent=2))
            return 0 if result["ready"] else 1
        if args.command == "formats":
            result = {"formats": list(FORMATS), "presets": PRESETS,
                      "always_written": ["sheet-NNN.png", "manifest.json"],
                      "optional_preview": ["preview.png", "preview.gif"]}
        elif args.command == "probe":
            result = probe(args.input)
        elif args.command == "validate":
            result = validate_manifest(args.manifest)
        elif args.command == "mcp":
            from .mcp_server import main as mcp_main
            mcp_main()
            return 0
        else:
            values = dict(PRESETS.get(args.preset, {}))
            if args.config:
                config = json.loads(args.config.read_text(encoding="utf-8"))
                if not isinstance(config, dict):
                    raise ConversionError("Config must contain a JSON object.")
                values.update(config)
            values.update({f.name: getattr(args, f.name) for f in fields(Options) if hasattr(args, f.name)})
            if args.frame_size:
                values.update(frame_width=args.frame_size[0], frame_height=args.frame_size[1])
            result = summary(convert(args.input, args.output, Options.from_dict(values)))
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (ConversionError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
