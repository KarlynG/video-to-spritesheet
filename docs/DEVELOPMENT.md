# Development and preview generation

Run from the repository root.

```bash
python -m pip install -e ".[mcp]"
python -m unittest discover -s tests -v
python scripts/create_demo.py
python scripts/create_social_preview.py
```

The tests exercise FFmpeg conversion, engine export geometry/pivots, multi-page Phaser helper execution with Node.js, and a real MCP SDK client/server handshake. They do not launch Unity or Unreal. `scripts/create_demo.py` converts the included knight video and rebuilds the README visuals from the real output, including `docs/sheet-preview.png`, a downscaled copy of the real sheet that keeps the README fast to load. The small procedural robot remains a reproducible test fixture; those tests need an FFmpeg build with `libx264`. CI runs the suite on Ubuntu, Windows, and macOS.

The demo creates a synchronized comparison in two formats: `docs/comparison.gif` (640×360 for the README) and `docs/comparison.mp4` (1280×720 H.264 for sharing). Both use the same 72 samples over six seconds. Each MP4 panel preserves the example's native 560×560 pixels. The GIF uses one shared palette and timing for both sides. Its checkerboard shows exported alpha; the PNG sheets remain the transparent deliverables.

`create_social_preview.py` builds `docs/social-preview.png` from the included video and actual exported PNG cells. The card is 1280×640 and under 1 MB for GitHub's social preview. Upload it in repository Settings → Social preview once the repository is public.

CI tests Python 3.10 and 3.12 on Ubuntu 24.04, Windows, and macOS 15 Intel. The explicit macOS label avoids capacity shortages affecting the ARM runners behind `macos-latest`.

## Releasing to PyPI

Bump `version` in `pyproject.toml`, then build and check from a clean checkout:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

The README uses absolute GitHub URLs so images and links also work on the PyPI project page.
