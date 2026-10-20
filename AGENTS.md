# Working with Video to Sprite Sheet

Use this repository to convert local videos into reproducible sprite sheets. Read
`skills/video-to-spritesheet/SKILL.md` before a conversion and `docs/FORMATS.md`
when the consumer requires a particular layout or metadata schema.

## Run a conversion

1. Run `python -m video_to_spritesheet doctor`; install this package and FFmpeg if needed.
2. Inspect the input with `python -m video_to_spritesheet probe INPUT`.
3. Translate the request into explicit frame size, sampling, grid, key color, and format.
4. Convert to a dedicated output directory. Preserve the original video.
5. Run `python -m video_to_spritesheet validate OUTPUT/manifest.json`.
6. Inspect `preview.png` and `preview.gif` for cut-off poses, color loss, and frame alignment.
7. Return the PNG sheets, metadata, preview, and any material warnings.

For Unity, Unreal Paper2D, or Phaser, select `unity`, `unreal-paper2d`, or `phaser`.
Read the generated `IMPORT.md` and `docs/ENGINES.md`, deliver all import files, and
distinguish export validation from actual engine compilation/import/playback.

Choose `--frames` or `--fps`, never both. Do not guess a key color. Keep aspect ratio
unless stretching is explicitly requested. If the requested format is unsupported,
read its authoritative specification and write a tested exporter from the manifest;
do not claim that a generic atlas is a native engine project file.

## Modify this project

- Keep conversion behavior in `src/video_to_spritesheet/core.py`; the CLI and MCP are adapters.
- Preserve the documented schema or explicitly version incompatible changes.
- Validate all options before constructing FFmpeg arguments. Use argument lists, never a shell.
- Keep MCP stdout exclusively for protocol traffic. Diagnostics belong on stderr.
- Keep generated frame names and page order deterministic. Preserve shared animation alignment.
- Add meaningful tests for conversion behavior and export compatibility changes.
- Run `python -m unittest discover -s tests -v` with FFmpeg and the MCP extra installed.
- Regenerate previews with `python scripts/create_demo.py` after changing the demo or visible behavior.
- Never replace the real conversion preview with a mockup or fabricated output.
