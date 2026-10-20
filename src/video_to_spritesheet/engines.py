"""Engine-specific import files derived from the canonical manifest."""

from __future__ import annotations

from importlib.resources import files
import json
from pathlib import Path
from typing import Any, Callable


def unity_descriptor(manifest: dict[str, Any]) -> dict[str, Any]:
    opt = manifest["options"]
    pages = manifest["pages"]
    return {"schema_version": 1, "engine": "unity", "pixels_per_unit": opt["pixels_per_unit"],
            "pivot": {"x": opt["pivot_x"], "y": opt["pivot_y"]},
            "frame_rate": manifest["selection"]["fps"], "resample": opt["resample"],
            "pages": [{key: page[key] for key in ("image", "width", "height")} for page in pages],
            "frames": [{"index": frame["index"], "name": frame["name"], "page": frame["page"],
                        "rect": {**frame["rect"], "y": pages[frame["page"]]["height"] - frame["rect"]["y"] - frame["rect"]["h"]}}
                       for frame in manifest["frames"]]}


def phaser_module(manifest: dict[str, Any]) -> str:
    pages = json.dumps([{key: p[key] for key in ("index", "image", "atlas")} for p in manifest["pages"]])
    sequence = json.dumps([{"page": f["page"], "frame": f["name"]} for f in manifest["frames"]])
    fps = json.dumps(manifest["selection"]["fps"])
    return f'''// Import these helpers into a Phaser scene. Load first; create the animation after loading.
const pages = {pages};
const sequence = {sequence};
export function preloadVideoSprites(scene, basePath, texturePrefix = "video") {{
  const base = basePath.replace(/\\/$/, "");
  for (const page of pages) {{
    scene.load.atlas(`${{texturePrefix}}_p${{page.index}}`, `${{base}}/${{page.image}}`, `${{base}}/${{page.atlas}}`);
  }}
}}
export function createVideoAnimation(scene, animationKey, texturePrefix = "video", repeat = -1) {{
  return scene.anims.create({{
    key: animationKey,
    frames: sequence.map(frame => ({{key: `${{texturePrefix}}_p${{frame.page}}`, frame: frame.frame}})),
    frameRate: {fps},
    repeat
  }});
}}
'''


def write_engine_export(directory: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    engine = manifest["options"]["format"]
    generated = ["IMPORT.md"]
    if engine == "unity":
        if any(max(p["width"], p["height"]) > 16384 for p in manifest["pages"]):
            from .core import ConversionError
            raise ConversionError("Unity exports require sheet dimensions <= 16384.")
        descriptor = unity_descriptor(manifest)
        (directory / "unity.json").write_text(json.dumps(descriptor, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        template = files("video_to_spritesheet").joinpath("templates/VideoToSpriteSheetImporter.cs").read_text(encoding="utf-8")
        (directory / "VideoToSpriteSheetImporter.cs").write_text(template, encoding="utf-8")
        generated += ["unity.json", "VideoToSpriteSheetImporter.cs"]
        instructions = """# Unity import

Target: Unity 2022.3+ with the 2D Sprite package installed.

1. Copy the PNG sheets, unity.json, and VideoToSpriteSheetImporter.cs into a dedicated folder under Assets.
   Keep only one copy of the C# helper in your project; reuse it for later exports.
2. Wait for script compilation. Select unity.json in the Project window.
3. Choose Tools > Video to Sprite Sheet > Import Selected Unity JSON.
4. The importer configures Multiple sprites, applies the exported rectangles/pivots/world scale,
   and creates animation.anim in the same folder. Drag that clip onto a SpriteRenderer object
   or add it to your Animator. Choose a suitable controller/state and looping behavior for your game.

Coordinates in unity.json already use Unity's bottom-left origin. The canonical manifest uses
top-left coordinates. Do not flip the PNG. The importer preserves existing sprite IDs on reimport
and asks before replacing an existing animation clip.

Export data is tested automatically. This helper still needs a smoke test in your Unity Editor version.
"""
    elif engine == "phaser":
        (directory / "phaser.mjs").write_text(phaser_module(manifest), encoding="utf-8")
        generated.append("phaser.mjs")
        instructions = """# Phaser import

Copy the PNG sheets, atlas JSON files, and phaser.mjs into your game's public asset folder.
Import preloadVideoSprites and createVideoAnimation from phaser.mjs in your scene module.
Call preloadVideoSprites(this, 'assets/character', 'character') from preload().
Call createVideoAnimation(this, 'character-run', 'character') from create().
Create a sprite using texture 'character_p0' and frame 'frame_000000', then play 'character-run'.

The helper loads every page, preserves exported frame order, and uses the conversion's FPS.
Its repeat argument defaults to -1 (loop forever); set 0 for one playback.
ES module syntax and the loading/animation calls are tested. Verify playback in your Phaser version.
"""
    else:
        generated += [p["atlas"] for p in manifest["pages"]]
        instructions = f"""# Unreal Engine / Paper2D import

1. Enable the Paper2D plugin in your Unreal project if needed.
2. Import each atlas-NNN.paper2dsprites descriptor into the Content Browser. Keep its PNG beside it.
   Paper2D reads the descriptor and imports the referenced texture and Sprite frames.
3. Select the imported Sprite Sheet asset and use Create Flipbooks, or select the frame Sprites
   in index order and choose Create Flipbook. For multiple pages, combine all frames in one Flipbook
   in the order listed by manifest.json; this export does not create a combined native .uasset.
4. Set Flipbook Frames Per Second to {manifest['selection']['fps']:.12g}.
5. Set sprite Pixels Per Unreal Unit as appropriate; the requested reference value is
   {manifest['options']['pixels_per_unit']:.12g}. The descriptor includes normalized pivot points
   but does not control every project-specific import setting.

Soft alpha edges may require a translucent sprite material; the default masked material can clip
them. The descriptor uses the TexturePacker-style Paper2D JSON layout, including pivot points.
Descriptors and frame geometry are tested automatically. Verify import/playback in your Unreal version.
"""
    (directory / "IMPORT.md").write_text(instructions, encoding="utf-8")
    return {"engine": engine, "files": generated, "editor_playback_verified": False}


def validate_engine_export(manifest: dict[str, Any], safe_file: Callable[[str], Path]) -> None:
    from .core import ConversionError
    export = manifest["engine_export"]
    if export["engine"] != manifest["options"]["format"]:
        raise ConversionError("Engine export does not match selected format.")
    required = {"IMPORT.md"}
    if export["engine"] == "unity":
        required.update(("unity.json", "VideoToSpriteSheetImporter.cs"))
    elif export["engine"] == "phaser":
        required.add("phaser.mjs")
    elif export["engine"] == "unreal-paper2d":
        required.update(p["atlas"] for p in manifest["pages"])
    else:
        raise ConversionError("Unsupported engine export.")
    if set(export["files"]) != required:
        raise ConversionError("Engine import file list is incomplete or unexpected.")
    for name in export["files"]:
        if not safe_file(name).is_file() or safe_file(name).stat().st_size == 0:
            raise ConversionError("Missing engine import file: " + name)
    if export["engine"] == "unity":
        data = json.loads(safe_file("unity.json").read_text(encoding="utf-8"))
        if data != unity_descriptor(manifest):
            raise ConversionError("Unity import data differs from the canonical manifest.")
        expected = files("video_to_spritesheet").joinpath("templates/VideoToSpriteSheetImporter.cs").read_text(encoding="utf-8")
        if safe_file("VideoToSpriteSheetImporter.cs").read_text(encoding="utf-8") != expected:
            raise ConversionError("Unity importer differs from its packaged template.")
    elif export["engine"] == "phaser":
        if safe_file("phaser.mjs").read_text(encoding="utf-8") != phaser_module(manifest):
            raise ConversionError("Phaser module differs from the canonical manifest.")
