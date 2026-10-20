---
name: video-to-spritesheet
description: Convert local videos into transparent PNG sprite sheets and engine import files using the video-to-spritesheet CLI. Use when asked to make sprite animations for Unity, Unreal Paper2D, or Phaser, extract frames, remove a flat-color video background, pack a requested grid or multiple sheets, export JSON atlases, or verify a video-to-sprite conversion.
---

# Video to Sprite Sheet

Use the installed `video_to_spritesheet` Python package. Run commands directly with
`python -m video_to_spritesheet`, or use this skill's `scripts/run.py` with the
Python interpreter where the package is installed. Read `references/formats.md`
when the requested output has specific dimensions, page layout, or metadata rules.

## Prepare

1. Run `python -m video_to_spritesheet doctor`.
2. If the package is missing, install it with `python -m pip install video-to-spritesheet`
   (or `python -m pip install -e /path/to/video-to-spritesheet` from a checkout). Install FFmpeg/FFprobe
   on PATH. Use a virtual environment where available; do not install unrelated tools.
3. Run `python -m video_to_spritesheet probe INPUT` and inspect duration, dimensions,
   and source FPS. Treat paths as local files, not remote URLs.

## Translate the request

- Set `--frame-size WIDTHxHEIGHT` for requested cell dimensions. Preserve the
  aspect ratio with `--fit contain` unless the user requests cropping or stretching.
- Choose `--frames N` for an exact sample count across the selected clip, or
  `--fps RATE` for a rate. Do not set both. The default rate is 12 fps.
- Set `--start` and `--end` in seconds for a clip. Split named animations into
  separate conversions and output directories unless implementing a dedicated exporter.
- Set `--columns` and `--rows` when a grid is specified. Overflow creates more pages
  with that same grid. Use `--padding` and `--spacing` only when required.
- Preserve background/decoded alpha unless a color removal setting is specified
  or the background color can be established by inspecting the input. Ask for a
  missing key color when it materially affects the result. Do not automatically
  apply the legacy green preset to arbitrary videos.
- Use `--preset legacy-green` for the original #00B140 workflow. Otherwise set
  `--key-color RRGGBB`, `--similarity`, and `--blend`; apply `--despill green` or
  `blue` only for a matching screen. Keying can remove matching colors in the subject.
- Use `--trim` only for a shared animation crop. It keeps the union alpha bounds
  across every frame, avoiding independent per-pose centering and jitter.
- Choose `unity`, `unreal-paper2d`, or `phaser` for those engines. Each export includes
  `IMPORT.md`; read it and deliver the required files together. Unity adds a C# Editor
  importer that slices sprites and creates a clip. Paper2D adds per-page descriptors;
  configure the Flipbook FPS and scale inside Unreal. Phaser adds a multi-page ES module.
- Use `--pixels-per-unit` for Unity world scale. `--pivot-x` and `--pivot-y` range 0..1,
  measured from the left and bottom. For bottom-center use `0.5` and `0`. Paper2D
  receives converted pivots; its pixel scale is a manual import setting. Read
  `docs/ENGINES.md` in the checkout when importing into an engine.
- Choose `json`, `texturepacker-hash`, or `texturepacker-array` for generic consumers.
  For another schema, read authoritative target documentation, write an explicit
  exporter from the manifest, and test it. Do not claim unsupported native exports.
- Use a dedicated output directory. Do not overwrite outputs without authorization.

## Convert and verify

```bash
python -m video_to_spritesheet convert character.webm --output output/character --frames 48 --frame-size 128x128 --columns 8 --rows 6 --preset legacy-green --format texturepacker-hash
python -m video_to_spritesheet validate output/character/manifest.json
```

Inspect `preview.png` and `preview.gif`. Confirm complete poses, correct frame order,
no unwanted key-color loss, consistent alignment, and sensible sampling. The GIF
is a checkerboard preview with rounded timing; deliver the lossless RGBA PNGs.
Check the manifest against the user's requested frame count, cell size, grid,
page count, and export format. A valid generic manifest alone does not establish
compatibility with a custom engine format. Engine export files are checked by the
validator, but it does not launch Unity, Unreal, or Phaser. Report that limitation
unless you actually import and play the animation in the user's engine version.

Return paths to every generated sheet, metadata file, and preview, plus material
warnings (for example repeated frames from oversampling). Preserve the source video.
Do not claim that a clip loops seamlessly unless playback was actually inspected.

## MCP alternative

If the project's local MCP server is connected, call `conversion_options`, then
`inspect_video`, `convert_video`, `validate_spritesheet`, and `preview_spritesheet`.
Use paths within its configured `SPRITESHEET_ROOT`. The same Python converter powers
both interfaces; do not reimplement the image processing in a prompt.
