# Engine exports

Tell the agent your engine, animation name, frame size, sample count or FPS, background
color, and any pivot/scale requirements. It should choose the matching format and
deliver the PNGs, manifest, import files, and preview together.

All engine formats share the same extraction and packing options. Keying is opt-in;
the commands below use `--preset legacy-green` for the included green-screen demo.
For your own input, choose the actual background color or omit keying to keep alpha.

| Target | `--format` | Import data |
| --- | --- | --- |
| Unity 2022.3+ with 2D Sprite | `unity` | `unity.json` + generated C# Editor helper |
| Unreal Engine with Paper2D | `unreal-paper2d` | One `.paper2dsprites` descriptor per PNG page |
| Phaser | `phaser` | One JSON hash atlas per page + `phaser.mjs` |

## Unity

```bash
video-to-spritesheet convert examples/robot.mp4 --output output/unity --preset legacy-green --frames 24 --frame-size 64x64 --columns 6 --rows 4 --format unity --pixels-per-unit 64 --pivot-x 0.5 --pivot-y 0
```

1. Install Unity's **2D Sprite** package in Package Manager.
2. Copy the PNG sheets, `unity.json`, and `VideoToSpriteSheetImporter.cs` into a
   dedicated folder under `Assets`. Keep only one copy of the helper in the project;
   reuse it when importing additional exports.
3. Wait for script compilation. Select `unity.json` in the Project window.
4. Run **Tools > Video to Sprite Sheet > Import Selected Unity JSON**.
5. The helper configures Multiple sprites, disables texture rescaling/mipmaps,
   applies all frame rectangles, normalized pivots, and pixels per unit, then creates
   `animation.anim`. It uses point filtering for `nearest`, bilinear for `lanczos`.
6. Drag the clip onto a GameObject with a SpriteRenderer, or add it to an Animator
   controller. Preview it and confirm scale, pivot, alpha, frame order, and looping.

`--pivot-x` measures from the left; `--pivot-y` measures from the bottom. Values
range from 0 to 1. Defaults are the center `(0.5, 0.5)`; `(0.5, 0)` is bottom-center.
Pivots refer to the full processed frame, including transparent content margins.
`--pixels-per-unit` defaults to 100. For a 64-pixel cell to span one world unit,
use 64. The helper preserves sprite IDs by name during reimport and asks before
replacing an existing generated animation clip.

The PNG and canonical manifest retain their top-left origin. Only `unity.json`
converts frame Y coordinates to Unity's bottom-left origin. Do not flip the image.
Every page must fit within 16384 pixels per side; use smaller pages as needed for
your target platform. Platform texture import overrides may need project-specific adjustment.

The converter emits the import data and helper. Unity creates its own native assets
when the helper runs. It does not generate an entire Unity project or controller.
The importer targets the [Sprite Editor Data Provider API](https://docs.unity3d.com/2022.3/Documentation/Manual/Sprite-data-provider-api.html).

## Unreal Engine / Paper2D

```bash
video-to-spritesheet convert examples/robot.mp4 --output output/unreal --preset legacy-green --frames 24 --frame-size 64x64 --columns 6 --rows 4 --format unreal-paper2d --pivot-x 0.5 --pivot-y 0
```

1. Enable **Paper2D** in your Unreal project if needed.
2. Import `atlas-001.paper2dsprites` into the Content Browser, keeping its matching
   `sheet-001.png` beside it. Repeat for additional pages. The descriptor identifies
   the texture, frame regions, names, and normalized pivot points.
3. Use **Create Flipbooks** on a Sprite Sheet asset, or select frame Sprites in
   index order and choose **Create Flipbook**. For multiple pages, combine all
   frames in the order recorded in `manifest.json`.
4. Set **Frames Per Second** to `selection.fps` from the manifest (also printed in
   the generated `IMPORT.md`). Do not assume that the importer uses JSON duration values.
5. Set **Pixels Per Unreal Unit** in the sprite assets for your game's world scale.
   `--pixels-per-unit` is recorded as guidance in `IMPORT.md`; the descriptor does
   not automatically apply this setting.
6. Review texture filtering and compression. For crisp pixel art, use **Sprite
   Actions > Apply Paper 2D Import Settings**. Soft alpha may need a translucent
   sprite material because a masked material can cut off partially transparent edges.
7. Preview the Flipbook and verify frame order, pivot, alpha, scale, and loop timing.

The descriptor is JSON in the TexturePacker-style Paper2D layout, with `frame`,
`rotated`, `trimmed`, `spriteSourceSize`, `sourceSize`, and `pivot` entries plus
texture metadata. It keeps top-left frame coordinates. The CLI's bottom-origin
pivot Y is converted to a top-origin value (`1 - pivot_y`). No rotations or per-frame
trimming are used. Native `.uasset` files and a combined multi-page Flipbook are
created/configured inside Unreal, not written by the converter.

See Epic's [sprite-sheet importing guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/import-sprites-in-unreal-engine)
and [Paper2D texture settings](https://dev.epicgames.com/documentation/unreal-engine/how-to-import-and-use-paper-2d-sprites-in-unreal-engine).

## Phaser

```bash
video-to-spritesheet convert examples/robot.mp4 --output output/phaser --preset legacy-green --frames 24 --frame-size 64x64 --columns 4 --rows 4 --format phaser
```

Copy the PNG pages, atlas JSON files, and `phaser.mjs` into your public assets.
Import the generated helpers into your scene module:

```javascript
import { preloadVideoSprites, createVideoAnimation } from './assets/robot/phaser.mjs';

// Inside your Phaser scene:
preload() {
  preloadVideoSprites(this, 'assets/robot', 'robot');
}

create() {
  createVideoAnimation(this, 'robot-run', 'robot');
  this.add.sprite(200, 200, 'robot_p0', 'frame_000000').play('robot-run');
}
```

The helper loads each page with `scene.load.atlas`, combines frames across pages
in export order, and uses the sampled FPS. Its fourth argument is the repeat count:
`-1` loops (default), `0` plays once. The texture prefix is customizable so different
exports can coexist. Pivot/scale options apply to Unity and Paper2D as described
above; set the Phaser GameObject's origin and scale in your scene as needed.

These are ES module helpers for the Phaser atlas/animation APIs. The generic
`texturepacker-hash` and `texturepacker-array` formats also work for consumers
that prefer to manage their own loading and animation setup.

## Verification status

Automated tests run actual FFmpeg conversions, check PNG geometry/transparency,
Unity coordinate conversion and world-scale data, Paper2D pivots/descriptors,
and multi-page order. Node.js executes the Phaser helper against recorded loader
and animation calls. CLI and MCP expose the same engine options.

**Unity and Unreal Editor compilation, import, and playback have not been exercised
in this repository's CI. Phaser browser playback is also an integration check.**
Engine exports include `editor_playback_verified: false` in the manifest. Import
and play the result in your engine version before marking an integration verified.
The regular `validate` command checks export files; it does not launch an engine.
