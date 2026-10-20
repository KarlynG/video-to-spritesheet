"""Run the installed converter without relying on console-script PATH discovery."""

import sys

try:
    from video_to_spritesheet.cli import main
except ImportError:
    print("Install the project into this Python environment first: python -m pip install -e /path/to/video-to-spritesheet", file=sys.stderr)
    raise SystemExit(2)

raise SystemExit(main())
