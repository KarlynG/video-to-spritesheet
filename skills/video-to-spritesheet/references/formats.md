# Output selection

Use the canonical `manifest.json` to verify a conversion or to implement another
exporter. All exports use uniform-size RGBA cells, row-major order, zero-based
frame indices, and no rotation. Alpha borders and gaps are excluded from frame
rectangles. All frames have equal sampled duration; original variable timing is
not preserved. Page filenames start at `sheet-001.png`.

| Requested output | Converter choice |
| --- | --- |
| PNG grid and complete frame/timing metadata | `--format json` |
| Named frames in a JSON object | `--format texturepacker-hash` |
| Frames in a JSON array with filename fields | `--format texturepacker-array` |
| Unity sprites and an animation import helper | `--format unity` |
| Unreal Paper2D sprite-sheet descriptors | `--format unreal-paper2d` |
| Phaser atlases plus multi-page animation helpers | `--format phaser` |
| Another engine schema or resource | Convert to the manifest, then implement and test an explicit exporter |

For N frames in C columns and R rows, each page holds C*R frames; another page is
created on overflow. Fixed grid pages retain their full size even when partly
filled. Frame names are unique across pages. Each optional atlas describes one
page; consumers must load all pages themselves.

With cell width W, height H, border P, and gap S, the content origin for local
frame i is `x = (i % C) * (W + 2P + S) + P`,
`y = (i // C) * (H + 2P + S) + P`.
Sheet dimensions are `C*(W+2P)+(C-1)*S` by `R*(H+2P)+(R-1)*S`.

TexturePacker-style exports set `rotated` and `trimmed` to false and include
`frame`, `spriteSourceSize`, `sourceSize`, and `duration` in milliseconds.
Engine formats add `IMPORT.md` with their import steps. Unity converts rectangles
to bottom-origin in `unity.json`, preserves bottom-origin normalized pivots, and
uses `pixels_per_unit`. Its generated C# helper creates native assets in Unity.
Paper2D retains top-origin rectangles and converts pivot Y to `1 - pivot_y`; set
Flipbook FPS and pixel scale in Unreal. Phaser's ES module loads every page and
builds one ordered animation. Engine editor playback still requires verification.
Edge extrusion, named animation groups, Godot resources, and Aseprite projects
are outside the built-in formats.

Read `docs/FORMATS.md` in the project checkout for the complete contract and sample JSON.
