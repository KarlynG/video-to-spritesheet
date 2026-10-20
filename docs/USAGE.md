# Manual usage

Install the package, then run these commands from any directory. The example paths refer to files in a clone of this repository.

## Installation

Requires **Python 3.10+** and **FFmpeg 5+**, including `ffprobe`, on your PATH. Works without ImageMagick or PowerShell. Install FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html), or use your OS package manager:

```text
Windows:  winget install --id Gyan.FFmpeg -e
macOS:    brew install ffmpeg
Ubuntu:   sudo apt-get install ffmpeg
```

Install the package from PyPI. [pipx](https://pipx.pypa.io/) or [uv](https://docs.astral.sh/uv/) keep it in its own environment:

```bash
pipx install video-to-spritesheet     # or: uv tool install video-to-spritesheet
video-to-spritesheet doctor
```

`python -m pip install video-to-spritesheet` inside a virtual environment works too. `python -m video_to_spritesheet` works wherever the console command does.

To work from source instead, clone the repository and install it in editable mode:

```bash
git clone https://github.com/KarlynG/video-to-spritesheet.git
cd video-to-spritesheet
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on macOS/Linux, or `.venv\Scripts\Activate.ps1` in Windows PowerShell. Then run `python -m pip install -e .`.

## CLI examples

```bash
# Keep the original background/alpha, sample at 12 fps, choose a grid automatically.
video-to-spritesheet convert animation.mp4 --output output/animation

# Exactly 48 samples in an 8x6 sheet with 128x128 transparent cells.
video-to-spritesheet convert animation.mp4 --output output/character --frames 48 --frame-size 128x128 --columns 8 --rows 6 --key-color 00B140 --despill green

# Reproduce the knight demonstration, including the sprite sheet and Phaser helper.
video-to-spritesheet convert examples/knight/input.mp4 --output output/knight --config examples/knight/options.json

# Select a clip, use another key color, and add borders/gaps.
video-to-spritesheet convert animation.mov --output output/walk --start 1 --end 3 --fps 12 --key-color FF00FF --padding 2 --spacing 1

# Use fixed grids and write multiple sheets when the frames do not fit on one page.
video-to-spritesheet convert animation.mp4 --output output/pages --frames 48 --frame-size 64x64 --columns 4 --rows 4 --format texturepacker-array

# Export Unity sprites and an Editor importer with a bottom-center pivot.
video-to-spritesheet convert animation.mp4 --output output/unity --format unity --pixels-per-unit 100 --pivot-x 0.5 --pivot-y 0

# Export Unreal Paper2D descriptors or Phaser atlases and animation helpers.
video-to-spritesheet convert animation.mp4 --output output/unreal --format unreal-paper2d
video-to-spritesheet convert animation.mp4 --output output/phaser --format phaser

# Inspect the input and verify the output files, not just the command's exit code.
video-to-spritesheet probe examples/robot.mp4
video-to-spritesheet validate examples/output/manifest.json
```

Run `video-to-spritesheet convert --help` for every option. Commands return JSON; errors go to stderr with a nonzero exit status. Existing output files require explicit `--overwrite`. The source video is never modified.

### Output

| File | Contents |
| --- | --- |
| `sheet-001.png`, `sheet-002.png`, ... | Lossless RGBA cells in row-major order |
| `manifest.json` | All pages, ordered frames, cell rectangles, sampling times, durations, settings, and warnings |
| `atlas-001.json`, ... | Optional TexturePacker-style JSON hash or array, one atlas per page |
| `unity.json`, `VideoToSpriteSheetImporter.cs` | Unity slicing, pivot, scale, and animation import data/helper when selected |
| `atlas-001.paper2dsprites`, ... | Unreal Paper2D descriptors when selected |
| `phaser.mjs` | Multi-page Phaser loading and animation helpers when selected |
| `IMPORT.md` | Import steps for the selected engine |
| `preview.png` | First sheet displayed on a checkerboard |
| `preview.gif` | Playback on a checkerboard; timing is rounded to GIF's 10 ms units |

Choose an engine format from the table above, `json` for just the PNG sheets and canonical manifest, or `texturepacker-hash` / `texturepacker-array` for a generic atlas export. Unity creates its native `.anim` inside the Editor using the generated helper; Unreal creates native assets on import. See [engine imports](ENGINES.md) and [the format contract](FORMATS.md).

### Sizing, sampling, and transparency

- `--frames N` samples the chosen time range uniformly; `--fps N` selects a rate. Choose one. Sampling above the video's source rate can repeat frames.
- Omit `--frame-size` to keep extracted dimensions. `--fit contain` preserves aspect ratio and adds transparent margins; `cover` crops; `stretch` distorts to fit. Nearest-neighbor resampling is the default; use `--resample lanczos` for smooth artwork.
- Omit `--key-color` to preserve decoded alpha and background. Color keying removes a chosen flat color; it does not segment arbitrary scenery. Similar colors on the character can also disappear. Inspect the preview.
- `--preset legacy-green` uses `#00B140`, similarity `0.12`, blend `0.04`, and green despill. The default sample rate is 12 fps.
- `--trim` crops **all frames to one shared alpha bounding box** before resizing. This preserves frame-to-frame alignment. It does not trim each pose independently.
- Explicit rows/columns fix the page grid. Extra frames create additional pages. Automatic layout respects `--max-sheet-size` (default 4096).
- Conversion has frame, pixel, and extraction-time limits. Raise them deliberately for large assets; lower FPS or source resolution for long/high-resolution clips.

### Configuration files

```bash
video-to-spritesheet convert animation.mp4 --output output/custom --config examples/options.json
```

Configuration keys use Python-style names such as `frame_count`, `frame_width`, and `key_color`. Precedence is defaults, then preset, then config, then explicit CLI flags. Unknown options fail. See [options.schema.json](options.schema.json).

## Python API

```python
from video_to_spritesheet import Options, convert, validate_manifest

result = convert("character.mp4", "output/character", Options(
    frame_count=24, frame_width=64, frame_height=64,
    columns=6, rows=4, key_color="00B140", despill="green",
))
print(validate_manifest(result["manifest"]))
```
