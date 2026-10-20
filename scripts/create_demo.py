"""Rebuild the knight README visuals from the included video and real converter output.

Run after installing the project: python scripts/create_demo.py
The procedural robot helpers also provide small deterministic test inputs.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont, ImageOps

from video_to_spritesheet import Options, convert, validate_manifest
from video_to_spritesheet.core import checkerboard


ROOT = Path(__file__).resolve().parents[1]


def robot_frame(index: int, total: int = 24) -> Image.Image:
    """A 64x64 pixel robot with a moving scarf and a synchronized idle bob."""
    im = Image.new("RGB", (64, 64), "#00B140")
    d = ImageDraw.Draw(im)
    phase = 2 * math.pi * index / total
    bob = round(math.sin(phase) * 2)
    x, y = 20, 17 + bob
    dark, armor, light = "#192735", "#6E95B3", "#B7D8E9"
    # Pixel-aligned coordinates intentionally keep this example reproducible.
    d.rectangle((x + 3, y + 26, x + 9, y + 36), fill=dark)
    d.rectangle((x + 15, y + 26, x + 21, y + 36), fill=dark)
    d.rectangle((x + 1, y + 35, x + 10, y + 38), fill=armor)
    d.rectangle((x + 14, y + 35, x + 23, y + 38), fill=armor)
    d.rectangle((x + 1, y + 15, x + 23, y + 28), fill=dark)
    d.rectangle((x + 3, y + 16, x + 21, y + 26), fill=armor)
    d.rectangle((x + 5, y + 17, x + 8, y + 25), fill=light)
    d.rectangle((x + 10, y + 21, x + 16, y + 24), fill="#EAB56B")
    d.rectangle((x - 4, y + 17, x, y + 29), fill=dark)
    d.rectangle((x - 3, y + 18, x - 1, y + 25), fill=armor)
    d.rectangle((x + 24, y + 17, x + 28, y + 29), fill=dark)
    d.rectangle((x + 25, y + 18, x + 27, y + 25), fill=armor)
    d.rectangle((x, y, x + 24, y + 15), fill=dark)
    d.rectangle((x + 2, y + 2, x + 22, y + 13), fill=armor)
    d.rectangle((x + 3, y + 3, x + 21, y + 6), fill=light)
    d.rectangle((x + 4, y + 8, x + 20, y + 12), fill=dark)
    eye_h = 0 if index in (10, 11) else 2
    d.rectangle((x + 7, y + 9, x + 9, y + 9 + eye_h), fill="#75F0DB")
    d.rectangle((x + 15, y + 9, x + 17, y + 9 + eye_h), fill="#75F0DB")
    d.rectangle((x + 11, y - 4, x + 13, y - 1), fill=dark)
    d.rectangle((x + 10, y - 6, x + 14, y - 4), fill="#EF9B55")
    scarf_y = y + 15 + round(math.sin(phase + 0.8) * 2)
    d.polygon([(x + 20, y + 14), (x + 37, scarf_y - 3), (x + 34, scarf_y + 2),
               (x + 36, scarf_y + 5), (x + 20, y + 18)], fill="#DA633F")
    d.rectangle((x + 1, y + 14, x + 23, y + 17), fill="#EF9B55")
    return im


def create_video(path: Path, count: int = 24) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        for i in range(count):
            robot_frame(i, count).save(Path(temp) / f"frame-{i:03d}.png")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "12",
                        "-i", str(Path(temp) / "frame-%03d.png"), "-c:v", "libx264", "-crf", "0",
                        "-pix_fmt", "yuv444p", "-threads", "1", str(path)], check=True)


def _font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default(size=size)


def create_hero(source_frame: Image.Image, output: Path, manifest: dict) -> None:
    canvas = Image.new("RGB", (1600, 1080), "#0D121A")
    d = ImageDraw.Draw(canvas)
    fg, muted, accent = "#EDF3FA", "#94A5BA", "#75F0CA"
    d.text((60, 40), "VIDEO TO SPRITE SHEET", font=_font(17, True), fill=accent)
    d.text((56, 77), "Video in. Sprite sheet out.", font=_font(54, True), fill=fg)
    d.text((60, 148), "Real conversion  /  72 frames  /  RGBA PNG + atlas + engine helpers", font=_font(22), fill=muted)

    def card(box, title, subtitle):
        d.rounded_rectangle(box, radius=20, fill="#151E2B", outline="#2B3A4C", width=2)
        x, y = box[:2]
        d.text((x + 24, y + 22), title, font=_font(22, True), fill=fg)
        d.text((x + 24, y + 60), subtitle, font=_font(16), fill=muted)

    card((50, 210, 455, 835), "01  SOURCE VIDEO", "Knight animation  /  green background")
    canvas.paste(source_frame.resize((335, 335), Image.Resampling.LANCZOS), (85, 355))
    d.text((85, 740), "6-second selection  /  12 fps output", font=_font(17), fill=muted)
    cell = manifest["frame_size"]
    page = manifest["pages"][0]
    card((485, 210, 1550, 835), "02  ACTUAL SPRITE SHEET",
         f'{manifest["frame_count"]} frames  /  {cell["w"]} x {cell["h"]} cells  /  '
         f'{page["columns"]} columns x {page["rows"]} rows')
    with Image.open(output / manifest["pages"][0]["image"]) as sheet:
        sheet = sheet.resize((1008, 504), Image.Resampling.LANCZOS)
        bg = checkerboard(sheet.size, 10)
        bg.paste(sheet, mask=sheet.getchannel("A"))
        canvas.paste(bg, (514, 307))
    for col in range(13):
        x = 514 + col * 84
        d.line((x, 307, x, 811), fill="#445269", width=1)
    for row in range(7):
        y = 307 + row * 84
        d.line((514, y, 1522, y), fill="#445269", width=1)
    for index in range(72):
        d.text((518 + (index % 12) * 84, 309 + (index // 12) * 84), f"{index:02}", font=_font(10), fill=muted)
    d.rounded_rectangle((50, 865, 1550, 1025), radius=18, fill="#080D14", outline="#2B3A4C", width=2)
    d.text((78, 885), "REPRODUCE THIS OUTPUT", font=_font(15, True), fill=accent)
    d.text((78, 927), "video-to-spritesheet convert examples/knight/input.mp4", font=_font(23), fill=fg)
    d.text((78, 965), "  --output examples/knight/output --config examples/knight/options.json --overwrite", font=_font(23), fill=accent)
    d.text((60, 1043), "The grid shows actual exported pixels. Checkerboards and frame labels appear only in this overview.", font=_font(16), fill=muted)
    canvas.save(ROOT / "docs" / "preview.png", optimize=True)


def save_sheet_preview(output: Path, manifest: dict, width: int = 1440) -> None:
    """Downscale the real first sheet so the README loads quickly; alpha is preserved."""
    with Image.open(output / manifest["pages"][0]["image"]) as sheet:
        height = round(width * sheet.height / sheet.width)
        preview = sheet.resize((width, height), Image.Resampling.LANCZOS)
    preview.save(ROOT / "docs" / "sheet-preview.png", optimize=True)


def save_preview_gif(frames: list[Image.Image], path: Path, durations) -> None:
    # Share a stable preview palette and avoid dithering noise in the GIFs.
    thumb_width = 160
    thumb_height = round(thumb_width * frames[0].height / frames[0].width)
    sample = Image.new("RGB", (9 * thumb_width, math.ceil(len(frames) / 9) * thumb_height))
    for index, frame in enumerate(frames):
        sample.paste(frame.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS),
                     ((index % 9) * thumb_width, (index // 9) * thumb_height))
    palette = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True)


def comparison_frame(source: Image.Image, result: Image.Image, manifest: dict) -> Image.Image:
    """Present the same sample in equal panels, using real source and RGBA pixels."""
    canvas = Image.new("RGB", (1280, 720), "#0D121A")
    draw = ImageDraw.Draw(canvas)
    ink, muted, accent = "#EDF3FA", "#A4B3C6", "#75F0CA"
    draw.text((48, 21), "VIDEO TO SPRITE SHEET", font=_font(32, True), fill=ink)
    draw.text((746, 28), "Video in. Game assets out.", font=_font(24, True), fill=accent)
    draw.text((48, 79), "SOURCE VIDEO", font=_font(18, True), fill=muted)
    draw.text((672, 79), "TRANSPARENT ANIMATION", font=_font(18, True), fill=muted)
    for image, x in ((source, 48), (result, 672)):
        preview = ImageOps.contain(image, (560, 560), Image.Resampling.LANCZOS)
        position = (x + (560 - preview.width) // 2, 112 + (560 - preview.height) // 2)
        if preview.mode == "RGBA":
            background = checkerboard((560, 560), 16)
            offset = (position[0] - x, position[1] - 112)
            background.paste(preview, offset, mask=preview.getchannel("A"))
            canvas.paste(background, (x, 112))
        else:
            canvas.paste(preview, position)
    draw.polygon(((630, 378), (650, 392), (630, 406)), fill=accent)
    size = manifest["frame_size"]
    draw.text((48, 691), f'{size["w"]} x {size["h"]} frames  /  '
              f'{manifest["frame_count"]} samples  /  {manifest["selection"]["fps"]:g} fps',
              font=_font(16), fill=muted)
    draw.text((826, 691), "github.com/KarlynG/video-to-spritesheet", font=_font(16), fill=accent)
    return canvas


def save_comparison(source_frames: list[Image.Image], result_frames: list[Image.Image],
                    manifest: dict, durations: list[int]) -> None:
    if not (len(source_frames) == len(result_frames) == len(durations) == manifest["frame_count"]):
        raise ValueError("Comparison frames and timings must match the manifest.")
    with tempfile.TemporaryDirectory() as temp:
        gif_frames = []
        for index, (source, result) in enumerate(zip(source_frames, result_frames)):
            frame = comparison_frame(source, result, manifest)
            frame.save(Path(temp) / f"frame-{index:03d}.png")
            gif_frames.append(frame.resize((640, 360), Image.Resampling.LANCZOS))
        save_preview_gif(gif_frames, ROOT / "docs" / "comparison.gif", durations)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                        "-framerate", str(manifest["selection"]["fps"]),
                        "-i", str(Path(temp) / "frame-%03d.png"), "-an", "-c:v", "libx264",
                        "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", "-threads", "1",
                        str(ROOT / "docs" / "comparison.mp4")], check=True)


def main() -> None:
    source = ROOT / "examples" / "knight" / "input.mp4"
    output = ROOT / "examples" / "knight" / "output"
    settings = json.loads((source.parent / "options.json").read_text(encoding="utf-8"))
    manifest = convert(source, output, Options.from_dict({**settings, "overwrite": True}))
    print(validate_manifest(output / "manifest.json"))
    save_sheet_preview(output, manifest)
    # Decode matching sample times and use lossless sheet cells directly.
    # The two sides are composed before any GIF resizing or quantization.
    fps = manifest["selection"]["fps"]
    # GIF timing has 10 ms precision. Distribute rounding so the loop stays 6 s.
    ticks = [round(i * 100 / fps) for i in range(manifest["frame_count"] + 1)]
    durations = [(end - start) * 10 for start, end in zip(ticks, ticks[1:])]
    with tempfile.TemporaryDirectory() as temp:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                        "-i", str(source), "-ss", str(manifest["selection"]["start_seconds"]),
                        "-t", str(settings["end"] - manifest["selection"]["start_seconds"]),
                        "-vf", f"fps={fps:.12g}:start_time=0",
                        "-frames:v", str(manifest["frame_count"]), "-threads", "1",
                        str(Path(temp) / "frame-%03d.png")], check=True)
        source_frames = []
        for path in sorted(Path(temp).glob("frame-*.png")):
            with Image.open(path) as frame:
                source_frames.append(frame.convert("RGB"))
        if len(source_frames) != manifest["frame_count"]:
            raise ValueError("Source and result previews must have matching frame counts.")
        create_hero(source_frames[6], output, manifest)
    frames = []
    for page in manifest["pages"]:
        with Image.open(output / page["image"]) as sheet:
            for entry in manifest["frames"]:
                if entry["page"] != page["index"]:
                    continue
                rect = entry["rect"]
                frame = sheet.crop((rect["x"], rect["y"],
                                    rect["x"] + rect["w"], rect["y"] + rect["h"]))
                frames.append(frame)
    save_comparison(source_frames, frames, manifest, durations)


if __name__ == "__main__":
    main()

