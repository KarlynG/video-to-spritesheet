# Sprite sheet format contract

## Image layout

Output sheets are lossless RGBA PNGs. Frame `0` is the first cell at the top left.
Frames advance left to right, then top to bottom; overflow continues on the next
sheet. Pages and frames are zero-indexed in metadata. Page filenames are one-indexed
(`sheet-001.png`). Unused cells are transparent. Frames are never rotated.

Each cell has a constant content size `frame_width x frame_height` and an optional
transparent border of `padding` pixels on each side. `spacing` is the gap between
padded cells. For local frame index `i` on a page:

```text
column = i % columns
row = i // columns
x = column * (frame_width + 2 * padding + spacing) + padding
y = row * (frame_height + 2 * padding + spacing) + padding
sheet_width  = columns * (frame_width + 2 * padding) + (columns - 1) * spacing
sheet_height = rows * (frame_height + 2 * padding) + (rows - 1) * spacing
```

The rectangle is the frame content, excluding its border and spacing. Borders
remain transparent; edge extrusion is not implemented. Every page uses the same
grid size, including a partially filled final page. Choosing both rows and columns
fixes page capacity; the converter never silently enlarges the requested grid.

## Canonical manifest (`--format json`)

`manifest.json` is always written, including when another format is selected.

```json
{
  "schema_version": 1,
  "frame_size": {"w": 64, "h": 64},
  "frame_count": 24,
  "duration_ms": 2000,
  "order": "row-major",
  "pages": [
    {"index": 0, "image": "sheet-001.png", "width": 384, "height": 256,
     "columns": 6, "rows": 4, "frame_count": 24}
  ],
  "frames": [
    {"index": 0, "name": "frame_000000", "page": 0,
     "rect": {"x": 0, "y": 0, "w": 64, "h": 64},
     "duration_ms": 83.333333, "sample_time_ms": 0}
  ]
}
```

This is an abbreviated illustration; a real manifest includes all frames plus
generator, source, selection, options, crop information, previews, and warnings.
It does not expose the source's absolute filesystem path.

`sample_time_ms` is the nominal uniform sampling timeline, relative to the start
of the source file. It is not an exact original variable-frame-rate timestamp.
All output frames have the same duration. `--frames N` samples the selected clip
at `N / clip_duration` FPS, so frames may be duplicated when sampling faster than
the source rate. This resampling deliberately does not preserve original VFR timing.
FFmpeg's FPS filter chooses the decoded source frames for that sampling timeline.

## TexturePacker-style JSON

`texturepacker-hash` writes a per-page `atlas-NNN.json` with frame names as keys:

```json
{
  "frames": {
    "frame_000000": {
      "frame": {"x": 0, "y": 0, "w": 64, "h": 64},
      "rotated": false,
      "trimmed": false,
      "spriteSourceSize": {"x": 0, "y": 0, "w": 64, "h": 64},
      "sourceSize": {"w": 64, "h": 64},
      "duration": 83.333333
    }
  },
  "meta": {
    "app": "video-to-spritesheet",
    "version": "0.1.0",
    "image": "sheet-001.png",
    "format": "RGBA8888",
    "size": {"w": 384, "h": 256},
    "scale": "1"
  }
}
```

`texturepacker-array` uses the same entries in a `frames` array; each entry has a
`filename` field instead of an object key. Frame names remain unique across pages.
These are atlas layouts, not files emitted by the commercial TexturePacker program.
Generic multi-page consumers must load each page's atlas. The `phaser` engine
format adds a helper that loads all pages and creates an ordered animation.

`--trim` crops the complete animation to one shared rectangle before resizing and
packing. Atlas frames therefore still have `trimmed: false`: every cell contains
the complete, consistently aligned processed frame. The original shared crop is
recorded in the canonical manifest, not as per-frame atlas trimming.

## Engine-specific formats

`phaser`, `unity`, and `unreal-paper2d` add explicit import files and `IMPORT.md`.
The manifest's `engine_export` records the engine, required files, and editor
verification status. See [engine imports](ENGINES.md) for usage and limitations.

Unity uses `unity.json` plus a packaged Editor importer. Its rectangles have
bottom-left Y coordinates, calculated as `page_height - manifest_y - frame_height`.
The normalized pivot is bottom-origin and pixels per unit sets world scale.

Paper2D uses per-page `atlas-NNN.paper2dsprites` JSON hash descriptors. Rectangles
remain top-left, while normalized pivot Y becomes `1 - pivot_y`. Pixel scale and
Flipbook FPS must be set in Unreal; the generated instructions provide the values.

## Custom targets

Use `manifest.json` as the authoritative input for another exporter. First confirm:

1. Exact consumer schema and version, including file naming and frame indexing.
2. Required row/column order, cell dimensions, borders, and page limits.
3. Timing units, animation names, loop behavior, and multi-page loading requirements.
4. Whether the consumer expects straight alpha (the PNGs here) or another convention.

Implement a dedicated adapter and test it against that contract. Unity `.anim`
assets are created inside Unity by the generated helper; Unreal native assets are
created on import. Godot `.tres`, Aseprite projects, and other native formats need
their own adapter.

## Verification

`video-to-spritesheet validate manifest.json` loads the referenced PNGs, checks
RGBA mode, dimensions, frame counts, in-bounds non-overlapping rectangles, frame
indices and page references, and correspondence with any exported atlas JSON.
It also verifies Unity import data, Paper2D pivot values, and engine helper files.
Asset references must stay in the manifest's own directory. Visual review is
still required to judge keying quality and whether the source actually loops.
