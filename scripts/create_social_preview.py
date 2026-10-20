"""Build the GitHub social card from the included video and actual exported PNGs.

Run after python scripts/create_demo.py:
    python scripts/create_social_preview.py
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

from video_to_spritesheet import validate_manifest
from video_to_spritesheet.core import checkerboard

ROOT = Path(__file__).resolve().parents[1]


def font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main() -> None:
    output = ROOT / "examples" / "knight" / "output"
    manifest_path = output / "manifest.json"
    validate_manifest(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["frames"][6]
    page = manifest["pages"][entry["page"]]
    rect = entry["rect"]
    with Image.open(output / page["image"]) as atlas:
        frame = atlas.crop((rect["x"], rect["y"],
                            rect["x"] + rect["w"], rect["y"] + rect["h"]))
        sheet = atlas.copy()
    source = ROOT / "examples" / "knight" / "input.mp4"
    with tempfile.TemporaryDirectory() as temp:
        source_png = Path(temp) / "source.png"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                        "-i", str(source), "-ss", str(entry["sample_time_ms"] / 1000),
                        "-frames:v", "1", "-threads", "1", str(source_png)], check=True)
        with Image.open(source_png) as source_image:
            source_frame = source_image.convert("RGB")
    canvas = Image.new("RGB", (1280, 640), "#0D121A")
    draw = ImageDraw.Draw(canvas)
    ink, muted, accent = "#EDF3FA", "#A4B3C6", "#75F0CA"
    draw.text((48, 29), "VIDEO TO SPRITE SHEET", font=font(17, True), fill=accent)
    draw.text((45, 63), "Video in. Game assets out.", font=font(48, True), fill=ink)
    draw.text((48, 126), "Transparent PNGs  /  animation atlases  /  engine exports",
              font=font(21), fill=muted)

    def card(box, title):
        draw.rounded_rectangle(box, radius=16, fill="#151E2B", outline="#304056", width=2)
        draw.text((box[0] + 18, box[1] + 17), title, font=font(16, True), fill=ink)

    card((48, 182, 414, 548), "01  SOURCE VIDEO")
    card((438, 182, 804, 548), "02  TRANSPARENT FRAME")
    card((828, 182, 1232, 548), "03  SPRITE SHEET")
    canvas.paste(source_frame.resize((264, 264), Image.Resampling.LANCZOS), (99, 230))
    preview = frame.resize((264, 264), Image.Resampling.LANCZOS)
    background = checkerboard(preview.size, 12)
    background.paste(preview, mask=preview.getchannel("A"))
    canvas.paste(background, (489, 230))
    sheet.thumbnail((368, 240), Image.Resampling.LANCZOS)
    background = checkerboard(sheet.size, 8)
    background.paste(sheet, mask=sheet.getchannel("A"))
    canvas.paste(background, (846 + (368 - sheet.width) // 2,
                              242 + (240 - sheet.height) // 2))
    size = manifest["frame_size"]
    draw.text((66, 514), f'{manifest["source"]["width"]} x {manifest["source"]["height"]} video',
              font=font(16), fill=muted)
    draw.text((456, 514), "Source resolution preserved", font=font(16), fill=accent)
    draw.text((846, 514), f'{manifest["frame_count"]} frames  /  {size["w"]} x {size["h"]} cells',
              font=font(16), fill=muted)
    for x in (422, 812):
        draw.polygon(((x, 352), (x + 11, 360), (x, 368)), fill=accent)
    draw.line((48, 574, 1232, 574), fill="#304056", width=1)
    draw.text((48, 595), "Unity  /  Unreal Paper2D  /  Phaser", font=font(18, True), fill=ink)
    draw.text((824, 595), "CLI  /  Python  /  AI agents + MCP", font=font(17), fill=accent)
    path = ROOT / "docs" / "social-preview.png"
    canvas.save(path, optimize=True)
    if path.stat().st_size >= 1_000_000:
        raise ValueError("Social preview must remain under 1 MB.")
    print(f"Saved {path.name}: 1280x640, {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
