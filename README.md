# Video to Sprite Sheet

Turn videos into **transparent PNG sprite sheets, animation metadata, and engine import files** with an AI agent or the CLI.

![Source video and transparent sprite animation playing in sync, side by side](https://raw.githubusercontent.com/KarlynG/video-to-spritesheet/main/docs/comparison.gif)

[Download MP4](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/comparison.mp4?raw=true) · [Download GIF](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/comparison.gif?raw=true)

Both sides show the same samples at the same size. The MP4 and exported frames preserve the source's **560×560** resolution; the GIF is a smaller preview.

## Why I built this

I made this for a game I'm working on. I animate my characters with AI video models, and every animation came out as an MP4, which no game engine can use directly. Pulling out frames, removing the background, and packing a sheet by hand for every single animation got old fast, so I automated it. Now one prompt to a coding agent turns a clip into an engine-ready sprite sheet.

## Example

**Actual sprite sheet: 72 frames · 560×560 cells · 12×6 grid · 12 fps**

![Transparent knight sprite sheet containing all 72 frames](https://raw.githubusercontent.com/KarlynG/video-to-spritesheet/main/docs/sheet-preview.png)

The preview above is scaled down. [Full-resolution PNG (6720×3360)](https://github.com/KarlynG/video-to-spritesheet/blob/main/examples/knight/output/sheet-001.png?raw=true) · [Atlas JSON](https://github.com/KarlynG/video-to-spritesheet/blob/main/examples/knight/output/atlas-001.json) · [Source video](https://github.com/KarlynG/video-to-spritesheet/blob/main/examples/knight/input.mp4?raw=true) · [Example settings](https://github.com/KarlynG/video-to-spritesheet/blob/main/examples/knight/options.json)

## Install

Requires **Python 3.10+** and **[FFmpeg 5+](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/USAGE.md#installation)** on your PATH.

```bash
pipx install video-to-spritesheet     # or: uv tool install video-to-spritesheet
video-to-spritesheet doctor
```

Plain `pip install video-to-spritesheet` works too. For the [MCP server](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/MCP.md), install `video-to-spritesheet[mcp]`.

## Use with an AI agent

Give Codex, Claude Code, or another coding agent this prompt:

> Use https://github.com/KarlynG/video-to-spritesheet. Read AGENTS.md and the bundled skill, install dependencies, and convert `character.mp4` for Unity into 48 transparent 128×128 frames in an 8×6 sheet. Remove background #00B140, inspect the preview, and validate the output.

Change the engine, dimensions, grid, and background color to match your asset.

[Agent instructions](https://github.com/KarlynG/video-to-spritesheet/blob/main/AGENTS.md) · [Skill](https://github.com/KarlynG/video-to-spritesheet/blob/main/skills/video-to-spritesheet/SKILL.md) · [Optional MCP setup](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/MCP.md)

## Manual use

```bash
video-to-spritesheet convert character.mp4 --output output/character --format unity
```

To reproduce the knight example, clone the repository and run:

```bash
video-to-spritesheet convert examples/knight/input.mp4 --output output/knight --config examples/knight/options.json
video-to-spritesheet validate output/knight/manifest.json
```

[CLI & Python guide](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/USAGE.md) · [Format reference](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/FORMATS.md) · [Development](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/DEVELOPMENT.md)

## Engine support

| Engine | Export |
| --- | --- |
| Unity 2022.3+ with 2D Sprite | PNGs + Editor importer for sprites and an animation clip |
| Unreal Engine / Paper2D | PNGs + `.paper2dsprites` descriptors for Flipbook setup |
| Phaser | JSON atlases + multi-page loading and animation helpers |

Also exports generic PNG grids and JSON hash/array atlases. Export files are tested; verify import and playback in your engine version. [Import guide →](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/ENGINES.md)

## Why sprite sheets?

A standard 2D animation workflow: share textures, batch rendering, and control individual frames. Frame count and resolution help manage memory; packing alone doesn't guarantee memory savings. [More about the benefits →](https://github.com/KarlynG/video-to-spritesheet/blob/main/docs/WHY.md)

## License

[MIT](https://github.com/KarlynG/video-to-spritesheet/blob/main/LICENSE). You can use, modify, and distribute this software, including commercially, provided you retain the copyright and license notice. The software is provided “as is,” without warranty.
