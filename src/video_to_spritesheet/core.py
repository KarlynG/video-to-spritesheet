"""Deterministic extraction, uniform-cell packing, and atlas verification."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageDraw, ImageOps

from . import __version__


class ConversionError(ValueError):
    """A user-actionable conversion or validation failure."""


FORMATS = ("json", "texturepacker-hash", "texturepacker-array", "phaser", "unity", "unreal-paper2d")
PRESETS = {
    "legacy-green": {"key_color": "00B140", "similarity": 0.12,
                     "blend": 0.04, "despill": "green"},
    "transparent": {"key_color": None, "despill": None},
}


@dataclass
class Options:
    fps: float | None = None  # Default 12; frame_count selects uniform sampling instead.
    frame_count: int | None = None
    start: float = 0.0
    end: float | None = None
    frame_width: int | None = None
    frame_height: int | None = None
    fit: str = "contain"
    resample: str = "nearest"
    columns: int | None = None
    rows: int | None = None
    padding: int = 0
    spacing: int = 0
    max_sheet_size: int = 4096
    max_frames: int = 600
    max_pixels: int = 64_000_000
    key_color: str | None = None
    similarity: float = 0.12
    blend: float = 0.04
    despill: str | None = None
    trim: bool = False
    format: str = "texturepacker-hash"
    pixels_per_unit: float = 100.0
    pivot_x: float = 0.5
    pivot_y: float = 0.5
    preview: bool = True
    overwrite: bool = False
    timeout: float = 300.0

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "Options":
        if not isinstance(values, dict):
            raise ConversionError("Options must be a JSON object.")
        unknown = values.keys() - {f.name for f in fields(cls)}
        if unknown:
            raise ConversionError("Unknown options: " + ", ".join(sorted(unknown)))
        result = cls(**values)
        result.check()
        return result

    def check(self) -> None:
        for name in ("start", "padding", "spacing", "max_sheet_size", "max_frames", "max_pixels",
                     "similarity", "blend", "timeout", "pixels_per_unit", "pivot_x", "pivot_y"):
            if getattr(self, name) is None:
                raise ConversionError(f"{name} must not be null.")
        for name in ("frame_count", "frame_width", "frame_height", "columns", "rows",
                     "max_frames", "max_sheet_size", "max_pixels"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 1):
                raise ConversionError(f"{name} must be a positive integer.")
        for name in ("padding", "spacing"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ConversionError(f"{name} must be a nonnegative integer.")
        for name in ("fps", "start", "end", "similarity", "blend", "timeout", "pixels_per_unit", "pivot_x", "pivot_y"):
            value = getattr(self, name)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ConversionError(f"{name} must be a finite number.")
        for name in ("trim", "preview", "overwrite"):
            if type(getattr(self, name)) is not bool:
                raise ConversionError(f"{name} must be a boolean.")
        if self.start < 0 or (self.end is not None and self.end <= self.start):
            raise ConversionError("Require 0 <= start < end (seconds).")
        if self.fps is not None and self.fps <= 0:
            raise ConversionError("fps must be positive.")
        if self.frame_count is not None and self.fps is not None:
            raise ConversionError("Choose frame_count or fps, not both.")
        if self.frame_count is not None and self.frame_count > self.max_frames:
            raise ConversionError("frame_count exceeds max_frames.")
        if bool(self.frame_width) != bool(self.frame_height):
            raise ConversionError("Set both frame_width and frame_height.")
        if self.fit not in ("contain", "cover", "stretch"):
            raise ConversionError("fit must be contain, cover, or stretch.")
        if self.resample not in ("nearest", "lanczos"):
            raise ConversionError("resample must be nearest or lanczos.")
        if self.format not in FORMATS:
            raise ConversionError("format must be one of: " + ", ".join(FORMATS))
        if self.pixels_per_unit <= 0 or not 0 <= self.pivot_x <= 1 or not 0 <= self.pivot_y <= 1:
            raise ConversionError("pixels_per_unit must be positive; pivot_x and pivot_y must be 0..1.")
        if self.key_color is not None:
            if not isinstance(self.key_color, str):
                raise ConversionError("key_color must be an RGB hex string.")
            color = self.key_color.removeprefix("#").removeprefix("0x")
            if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
                raise ConversionError("key_color must have six RGB hex digits.")
            self.key_color = color.upper()
        if not 0.01 <= self.similarity <= 1 or not 0 <= self.blend <= 1:
            raise ConversionError("similarity must be 0.01..1 and blend must be 0..1.")
        if self.despill not in (None, "green", "blue"):
            raise ConversionError("despill must be green, blue, or null.")
        if self.despill and not self.key_color:
            raise ConversionError("despill requires an explicit key_color.")
        if self.timeout <= 0:
            raise ConversionError("timeout must be positive.")


def _run(args: list[str], timeout: float = 300) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise ConversionError(f"{args[0]} is missing. Install FFmpeg and FFprobe on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ConversionError(f"{args[0]} exceeded its {timeout:g}s timeout.") from exc
    if result.returncode:
        raise ConversionError(f"{args[0]} failed:\n{result.stderr[-4000:].strip()}")
    return result.stdout


def _local_file(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise ConversionError(f"Input file does not exist: {resolved}")
    return resolved


def _positive_number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (ValueError, TypeError):
        return None


def probe(source: str | Path) -> dict[str, Any]:
    """Inspect a local video. No network URLs or shell commands are accepted."""
    source = _local_file(source)
    data = json.loads(_run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                            "-of", "json", str(source)], 60))
    streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"
               and not s.get("disposition", {}).get("attached_pic")]
    if not streams:
        raise ConversionError("The input contains no video stream.")
    stream = streams[0]
    try:
        rate = float(Fraction(stream.get("avg_frame_rate", "0/1")))
    except (ValueError, ZeroDivisionError):
        rate = 0.0
    return {"file": source.name, "stream_index": stream["index"],
            "width": stream["width"], "height": stream["height"],
            "duration_seconds": _positive_number(stream.get("duration"))
            or _positive_number(data.get("format", {}).get("duration")),
            "source_fps": rate, "codec": stream.get("codec_name"),
            "pixel_format": stream.get("pix_fmt")}


def _grid(count: int, width: int, height: int, opt: Options) -> tuple[int, int, int, int]:
    cw, ch = width + 2 * opt.padding, height + 2 * opt.padding
    max_cols = (opt.max_sheet_size + opt.spacing) // (cw + opt.spacing)
    max_rows = (opt.max_sheet_size + opt.spacing) // (ch + opt.spacing)
    if max_cols < 1 or max_rows < 1:
        raise ConversionError("One padded frame exceeds max_sheet_size.")
    cols = opt.columns
    rows = opt.rows
    if cols is None:
        cols = (min(max_cols, math.ceil(count / rows)) if rows else
                min(max_cols, max(1, math.ceil(math.sqrt(count * ch / cw)))))
    if rows is None:
        rows = min(max_rows, math.ceil(count / cols))
    if cols > max_cols or rows > max_rows:
        raise ConversionError("Requested grid exceeds max_sheet_size; reduce the grid or cell size.")
    return cols, rows, cols * cw + (cols - 1) * opt.spacing, rows * ch + (rows - 1) * opt.spacing


def checkerboard(size: tuple[int, int], cell: int = 8) -> Image.Image:
    image = Image.new("RGB", size, "#212833")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2 == 0:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill="#2b3543")
    return image


def _json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _atlas(page: dict[str, Any], frames: list[dict[str, Any]], opt: Options) -> dict[str, Any]:
    entries = {}
    for frame in frames:
        entries[frame["name"]] = {"frame": frame["rect"], "rotated": False, "trimmed": False,
                                  "spriteSourceSize": {"x": 0, "y": 0, "w": frame["rect"]["w"], "h": frame["rect"]["h"]},
                                  "sourceSize": {"w": frame["rect"]["w"], "h": frame["rect"]["h"]},
                                  "duration": frame["duration_ms"]}
    value: Any = entries
    if opt.format == "texturepacker-array":
        value = [{"filename": name, **entry} for name, entry in entries.items()]
    return {"frames": value, "meta": {"app": "video-to-spritesheet", "version": __version__,
                                       "image": page["image"], "format": "RGBA8888",
                                       "size": {"w": page["width"], "h": page["height"]}, "scale": "1"}}


def convert(source: str | Path, output: str | Path, options: Options | None = None) -> dict[str, Any]:
    """Convert a local video and return the verified manifest; never edit the input."""
    opt = options or Options()
    opt.check()
    source = _local_file(source)
    output = Path(output).expanduser().resolve()
    if output == source or (output.exists() and not output.is_dir()):
        raise ConversionError("Output must be a directory, separate from the source file.")
    info = probe(source)
    total_duration = info["duration_seconds"]
    end = opt.end if opt.end is not None else total_duration
    if total_duration and opt.start >= total_duration:
        raise ConversionError("start is outside the video duration.")
    if total_duration and end and end > total_duration + 0.05:
        raise ConversionError("end exceeds the video duration.")
    duration = end - opt.start if end is not None else None
    if opt.frame_count and not duration:
        raise ConversionError("Exact frame_count requires a known duration or an explicit end.")
    fps = opt.frame_count / duration if opt.frame_count else (opt.fps or 12.0)
    if duration and math.ceil(duration * fps - 1e-6) > opt.max_frames:
        raise ConversionError("Sampling exceeds max_frames; reduce fps, shorten the clip, or raise the limit.")
    if opt.frame_width and opt.frame_width * opt.frame_height > opt.max_pixels:
        raise ConversionError("A resized frame exceeds max_pixels.")
    expected_frames = opt.frame_count or (math.ceil(duration * fps - 1e-6) if duration else opt.max_frames)
    if info["width"] * info["height"] * expected_frames > opt.max_pixels:
        raise ConversionError("Decoded frames would exceed max_pixels; shorten or downsample the source video.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="video-spritesheet-", dir=output.parent) as temp:
        work = Path(temp)
        raw = work / "frames"
        raw.mkdir()
        filters = [f"fps={fps:.12g}:start_time=0", "format=rgba"]
        if opt.key_color:
            filters.append(f"colorkey=0x{opt.key_color}:{opt.similarity}:{opt.blend}")
        if opt.despill:
            filters.append(f"despill=type={opt.despill}:mix=0.5:expand=0.2")
        filters.append("format=rgba")
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-i", str(source), "-ss", str(opt.start)]
        if duration:
            args += ["-t", str(duration)]
        args += ["-map", f"0:{info['stream_index']}", "-an", "-sn", "-dn", "-vf", ",".join(filters),
                 "-frames:v", str(opt.frame_count or opt.max_frames + 1), "-fps_mode", "passthrough",
                 "-threads", "1", str(raw / "frame-%06d.png")]
        _run(args, opt.timeout)
        paths = sorted(raw.glob("frame-*.png"))
        if not paths:
            raise ConversionError("No frames were extracted from the selected time range.")
        if len(paths) > opt.max_frames:
            raise ConversionError("Extracted frames exceed max_frames.")
        if opt.frame_count and len(paths) != opt.frame_count:
            raise ConversionError(f"Requested {opt.frame_count} frames but extracted {len(paths)}; check the time range.")
        with Image.open(paths[0]) as image:
            source_size = image.size
        if source_size[0] * source_size[1] * len(paths) > opt.max_pixels:
            raise ConversionError("Decoded frames exceed max_pixels; shorten or downsample the source video.")
        crop_box = None
        for path in paths:
            with Image.open(path) as image:
                if image.size != source_size:
                    raise ConversionError("Extracted frames have inconsistent sizes.")
                if opt.trim:
                    box = image.convert("RGBA").getchannel("A").getbbox()
                    if box:
                        crop_box = box if crop_box is None else (min(crop_box[0], box[0]), min(crop_box[1], box[1]),
                                                               max(crop_box[2], box[2]), max(crop_box[3], box[3]))
        if opt.trim and crop_box is None:
            raise ConversionError("All frames are transparent after background removal.")
        native_size = (crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]) if crop_box else source_size
        size = (opt.frame_width, opt.frame_height) if opt.frame_width else native_size
        count = len(paths)
        if size[0] * size[1] * count > opt.max_pixels:
            raise ConversionError("Resized frames exceed max_pixels.")
        cols, rows, sw, sh = _grid(count, *size, opt)
        capacity = cols * rows
        page_count = math.ceil(count / capacity)
        if sw * sh > opt.max_pixels:
            raise ConversionError("One sheet exceeds max_pixels.")
        stage = work / "output"
        stage.mkdir()
        pages, frames, previews = [], [], []
        resample = Image.Resampling.NEAREST if opt.resample == "nearest" else Image.Resampling.LANCZOS
        for p in range(page_count):
            page = {"index": p, "image": f"sheet-{p + 1:03d}.png", "width": sw, "height": sh,
                    "columns": cols, "rows": rows, "frame_count": min(capacity, count - p * capacity)}
            if opt.format not in ("json", "unity"):
                extension = "paper2dsprites" if opt.format == "unreal-paper2d" else "json"
                page["atlas"] = f"atlas-{p + 1:03d}.{extension}"
            sheet = Image.new("RGBA", (sw, sh))
            page_frames = []
            for i in range(p * capacity, min(count, (p + 1) * capacity)):
                with Image.open(paths[i]) as img:
                    frame = img.convert("RGBA")
                if crop_box:
                    frame = frame.crop(crop_box)
                if frame.size != size:
                    if opt.fit == "contain":
                        scaled = ImageOps.contain(frame, size, method=resample)
                        frame = Image.new("RGBA", size)
                        frame.paste(scaled, ((size[0] - scaled.width) // 2, (size[1] - scaled.height) // 2))
                    elif opt.fit == "cover":
                        frame = ImageOps.fit(frame, size, method=resample)
                    else:
                        frame = frame.resize(size, resample=resample)
                local = i % capacity
                x = (local % cols) * (size[0] + opt.padding * 2 + opt.spacing) + opt.padding
                y = (local // cols) * (size[1] + opt.padding * 2 + opt.spacing) + opt.padding
                sheet.paste(frame, (x, y))  # Copy alpha directly: alpha_composite would change transparent RGB.
                entry = {"index": i, "name": f"frame_{i:06d}", "page": p,
                         "rect": {"x": x, "y": y, "w": size[0], "h": size[1]},
                         "duration_ms": round(1000 / fps, 6),
                         "sample_time_ms": round((opt.start + i / fps) * 1000, 6)}
                frames.append(entry)
                page_frames.append(entry)
                if opt.preview:
                    bg = checkerboard(size)
                    bg.paste(frame, mask=frame.getchannel("A"))
                    previews.append(bg)
            sheet.save(stage / page["image"])
            if "atlas" in page:
                atlas = _atlas(page, page_frames, opt)
                if opt.format == "unreal-paper2d":
                    for entry in atlas["frames"].values():
                        entry["pivot"] = {"x": opt.pivot_x, "y": 1 - opt.pivot_y}
                _json(stage / page["atlas"], atlas)
            pages.append(page)
        warnings = []
        if opt.frame_count and info["source_fps"] and fps > info["source_fps"]:
            warnings.append("Requested sampling exceeds source FPS; duplicate frames may occur.")
        manifest = {"schema_version": 1, "generator": {"name": "video-to-spritesheet", "version": __version__},
                    "source": info, "selection": {"start_seconds": opt.start, "end_seconds": end, "fps": fps},
                    "frame_size": {"w": size[0], "h": size[1]}, "frame_count": count,
                    "duration_ms": round(count * 1000 / fps, 6), "order": "row-major",
                    "crop_box": list(crop_box) if crop_box else None,
                    "options": asdict(opt), "pages": pages, "frames": frames, "warnings": warnings}
        if opt.format in ("phaser", "unity", "unreal-paper2d"):
            from .engines import write_engine_export
            manifest["engine_export"] = write_engine_export(stage, manifest)
        if opt.preview:
            # GIF is a checkerboard playback aid; the RGBA PNG sheets are the lossless deliverables.
            previews[0].save(stage / "preview.gif", save_all=True, append_images=previews[1:],
                             duration=max(10, round(1000 / fps / 10) * 10), loop=0, disposal=2)
            with Image.open(stage / pages[0]["image"]) as first_sheet:
                bg = checkerboard(first_sheet.size)
                bg.paste(first_sheet, mask=first_sheet.getchannel("A"))
                bg.save(stage / "preview.png")
            manifest["preview"] = {"image": "preview.png", "animation": "preview.gif"}
        _json(stage / "manifest.json", manifest)
        validate_manifest(stage / "manifest.json")
        generated = sorted(stage.iterdir())
        if output.exists():
            conflicts = [f.name for f in generated if (output / f.name).exists()]
            if conflicts and not opt.overwrite:
                raise ConversionError("Output files exist; choose another directory or use overwrite: " + ", ".join(conflicts))
            if any((output / f.name).resolve() == source for f in generated):
                raise ConversionError("An output path would overwrite the source video.")
        output.mkdir(parents=True, exist_ok=True)
        # Replace generated files only; unrelated files in the output directory are preserved.
        for path in generated:
            os.replace(path, output / path.name)
        return {**manifest, "output_directory": str(output), "manifest": str(output / "manifest.json")}


def validate_manifest(path: str | Path) -> dict[str, Any]:
    """Verify actual images, cell bounds, frame indices, and atlas correspondence."""
    path = _local_file(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["schema_version"] != 1 or data["order"] != "row-major":
            raise ConversionError("Unsupported manifest schema or ordering.")
        frames, pages = data["frames"], data["pages"]
        if len(frames) != data["frame_count"] or not frames or not pages:
            raise ConversionError("Manifest frame count is inconsistent.")
        w, h = data["frame_size"]["w"], data["frame_size"]["h"]
        padding, spacing = data["options"]["padding"], data["options"]["spacing"]
        if any(type(n) is not int or n < 0 for n in (padding, spacing)):
            raise ConversionError("Padding and spacing must be nonnegative integers.")
        if type(w) is not int or type(h) is not int or w < 1 or h < 1:
            raise ConversionError("Invalid frame dimensions.")
        by_page: dict[int, list[dict]] = {i: [] for i in range(len(pages))}
        names = set()
        for i, frame in enumerate(frames):
            if frame["index"] != i or frame["page"] not in by_page:
                raise ConversionError("Invalid frame index or page reference.")
            if not isinstance(frame["name"], str) or frame["name"] in names:
                raise ConversionError("Frame names must be unique strings.")
            names.add(frame["name"])
            if not isinstance(frame["duration_ms"], (int, float)) or not math.isfinite(frame["duration_ms"]) or frame["duration_ms"] <= 0:
                raise ConversionError("Frame duration must be positive and finite.")
            by_page[frame["page"]].append(frame)

        def safe_file(name: str) -> Path:
            if not isinstance(name, str) or Path(name).name != name or name in (".", ".."):
                raise ConversionError("Manifest assets must be filenames in its directory.")
            target = (path.parent / name).resolve()
            if target.parent != path.parent.resolve():
                raise ConversionError("Manifest asset escapes its directory.")
            return target

        for i, page in enumerate(pages):
            if page["index"] != i or page["frame_count"] != len(by_page[i]):
                raise ConversionError("Page frame count is inconsistent.")
            cols, rows = page["columns"], page["rows"]
            if any(type(n) is not int or n < 1 for n in (cols, rows)) or len(by_page[i]) > cols * rows:
                raise ConversionError("Invalid page grid or capacity.")
            expected_size = (cols * (w + 2 * padding) + (cols - 1) * spacing,
                             rows * (h + 2 * padding) + (rows - 1) * spacing)
            if (page["width"], page["height"]) != expected_size:
                raise ConversionError("Page dimensions do not match its grid, padding, and spacing.")
            with Image.open(safe_file(page["image"])) as image:
                image.load()
                if image.mode != "RGBA" or image.size != (page["width"], page["height"]):
                    raise ConversionError("Sheet must be RGBA and match the manifest dimensions.")
            rects = []
            for local_index, frame in enumerate(by_page[i]):
                r = frame["rect"]
                if any(type(r[k]) is not int for k in ("x", "y", "w", "h")):
                    raise ConversionError("Frame rectangles require integer coordinates.")
                if (r["w"], r["h"]) != (w, h) or min(r["x"], r["y"]) < 0 or r["x"] + w > page["width"] or r["y"] + h > page["height"]:
                    raise ConversionError("Frame rectangle is outside its sheet or has the wrong size.")
                expected_xy = ((local_index % cols) * (w + 2 * padding + spacing) + padding,
                               (local_index // cols) * (h + 2 * padding + spacing) + padding)
                if (r["x"], r["y"]) != expected_xy:
                    raise ConversionError("Frame rectangle does not follow the declared row-major grid.")
                rects.append(r)
            for a, r in enumerate(rects):
                if any(r["x"] < s["x"] + s["w"] and s["x"] < r["x"] + r["w"] and
                       r["y"] < s["y"] + s["h"] and s["y"] < r["y"] + r["h"] for s in rects[a + 1:]):
                    raise ConversionError("Frame rectangles overlap.")
            if "atlas" in page:
                atlas = json.loads(safe_file(page["atlas"]).read_text(encoding="utf-8"))
                if atlas["meta"]["image"] != page["image"] or atlas["meta"]["size"] != {"w": page["width"], "h": page["height"]}:
                    raise ConversionError("Atlas image metadata differs from the manifest.")
                entries = atlas["frames"]
                if isinstance(entries, list):
                    entries = {entry["filename"]: entry for entry in entries}
                if set(entries) != {frame["name"] for frame in by_page[i]}:
                    raise ConversionError("Atlas frame names differ from the manifest.")
                for frame in by_page[i]:
                    if entries[frame["name"]]["frame"] != frame["rect"]:
                        raise ConversionError("Atlas frame rectangle differs from the manifest.")
                    if data["options"]["format"] == "unreal-paper2d":
                        expected_pivot = {"x": data["options"]["pivot_x"], "y": 1 - data["options"]["pivot_y"]}
                        if entries[frame["name"]].get("pivot") != expected_pivot:
                            raise ConversionError("Paper2D pivot differs from the manifest.")
        if data["options"]["format"] in ("unity", "phaser", "unreal-paper2d") and "engine_export" not in data:
            raise ConversionError("Missing engine export metadata.")
        if "engine_export" in data:
            from .engines import validate_engine_export
            validate_engine_export(data, safe_file)
        return {"valid": True, "frame_count": len(frames), "page_count": len(pages), "frame_size": data["frame_size"]}
    except (OSError, KeyError, TypeError, json.JSONDecodeError, IndexError) as exc:
        raise ConversionError(f"Invalid manifest or missing asset: {exc}") from exc
