from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

from video_to_spritesheet import ConversionError, Options, convert, probe, validate_manifest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from create_demo import create_video


class OptionTests(unittest.TestCase):
    def test_invalid_options(self):
        cases = [{"frame_count": True}, {"fps": float("nan")}, {"rows": 0}, {"key_color": "red;echo fail"},
                 {"fps": 12, "frame_count": 4}, {"frame_width": 64}, {"start": -1}, {"start": 2, "end": 1},
                 {"padding": -1}, {"unknown": 1}, {"despill": "green"}, {"format": "unknown-engine"}, {"preview": "false"},
                 {"pixels_per_unit": 0}, {"pivot_x": 1.1}, {"pivot_y": -0.1}, {"pivot_y": None},
                 {"max_frames": None}, {"start": None}]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ConversionError):
                Options.from_dict(case)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg and FFprobe required")
class ConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="sprite tests ")
        cls.base = Path(cls.temp.name)
        cls.video = cls.base / "robot input.mp4"
        create_video(cls.video)
        cls.digest = hashlib.sha256(cls.video.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=self.base)
        self.output = Path(self.work.name) / "output"

    def tearDown(self):
        self.work.cleanup()
        self.assertEqual(hashlib.sha256(self.video.read_bytes()).hexdigest(), self.digest)

    def convert(self, **kwargs):
        return convert(self.video, self.output, Options(**kwargs))

    def test_exact_count_transparency_and_atlas(self):
        result = self.convert(frame_count=24, frame_width=64, frame_height=64, columns=6, rows=4,
                              key_color="00B140", despill="green")
        self.assertEqual(result["frame_count"], 24)
        self.assertEqual(validate_manifest(self.output / "manifest.json")["valid"], True)
        with Image.open(self.output / "sheet-001.png") as image:
            self.assertEqual(image.size, (384, 256))
            self.assertEqual(image.getpixel((0, 0))[3], 0)
            self.assertEqual(image.getpixel((32, 25))[3], 255)
        self.assertTrue((self.output / "preview.gif").is_file())

    def test_default_keeps_background(self):
        result = self.convert(frame_count=3, preview=False)
        with Image.open(self.output / result["pages"][0]["image"]) as image:
            self.assertEqual(image.getpixel((0, 0))[3], 255)
        self.assertFalse((self.output / "preview.gif").exists())

    def test_paging_and_padding(self):
        result = self.convert(frame_count=14, columns=3, rows=2, frame_width=32, frame_height=32,
                              padding=2, spacing=3, format="texturepacker-array", preview=False)
        self.assertEqual(len(result["pages"]), 3)
        self.assertEqual([p["frame_count"] for p in result["pages"]], [6, 6, 2])
        self.assertEqual(result["frames"][1]["rect"], {"x": 41, "y": 2, "w": 32, "h": 32})
        self.assertEqual(result["frames"][6]["rect"]["x"], 2)
        self.assertTrue(validate_manifest(self.output / "manifest.json")["valid"])

    def test_time_range_fps(self):
        result = self.convert(start=0.5, end=1.5, fps=6, preview=False)
        self.assertEqual(result["frame_count"], 6)
        self.assertAlmostEqual(result["duration_ms"], 1000)
        self.assertEqual(result["frames"][0]["sample_time_ms"], 500)

    def test_shared_trim_and_contain(self):
        result = self.convert(frame_count=12, trim=True, key_color="00B140", frame_width=80, frame_height=40)
        self.assertIsNotNone(result["crop_box"])
        self.assertEqual(result["frame_size"], {"w": 80, "h": 40})
        self.assertEqual(len({(f["rect"]["w"], f["rect"]["h"]) for f in result["frames"]}), 1)

    def test_collision_preserves_outputs(self):
        self.convert(frame_count=2, preview=False)
        path = self.output / "sheet-001.png"
        digest = path.read_bytes()
        with self.assertRaisesRegex(ConversionError, "Output files exist"):
            self.convert(frame_count=3, preview=False)
        self.assertEqual(path.read_bytes(), digest)
        marker = self.output / "keep.txt"
        marker.write_text("keep")
        self.convert(frame_count=3, preview=False, overwrite=True)
        self.assertEqual(marker.read_text(), "keep")

    def test_invalid_range_limits_and_grid(self):
        for opts in ({"start": 10}, {"end": 20}, {"fps": 30, "max_frames": 4},
                     {"frame_count": 2, "columns": 20, "max_sheet_size": 100},
                     {"frame_count": 2, "max_pixels": 10}):
            with self.subTest(opts=opts), self.assertRaises(ConversionError):
                self.convert(**opts)
        self.assertFalse(self.output.exists())

    def test_tampered_image_and_atlas(self):
        self.convert(frame_count=2, preview=False)
        atlas = self.output / "atlas-001.json"
        data = json.loads(atlas.read_text())
        data["frames"]["frame_000000"]["frame"]["x"] += 1
        atlas.write_text(json.dumps(data))
        with self.assertRaisesRegex(ConversionError, "Atlas frame rectangle"):
            validate_manifest(self.output / "manifest.json")

    def test_reject_manifest_path_traversal(self):
        self.convert(frame_count=1, preview=False)
        path = self.output / "manifest.json"
        data = json.loads(path.read_text())
        data["pages"][0]["image"] = "../elsewhere.png"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ConversionError, "filenames"):
            validate_manifest(path)

    def test_grid_tampering_is_detected(self):
        self.convert(frame_count=4, columns=2, preview=False)
        path = self.output / "manifest.json"
        data = json.loads(path.read_text())
        data["pages"][0]["columns"] = 4
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ConversionError, "Page dimensions"):
            validate_manifest(path)

    def test_cli_config_and_machine_output(self):
        config = self.base / "options.json"
        config.write_text(json.dumps({"frame_count": 4, "columns": 2, "preview": False}))
        result = subprocess.run([sys.executable, "-m", "video_to_spritesheet", "convert", str(self.video),
                                 "-o", str(self.output), "--config", str(config), "--columns", "4"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["pages"][0]["columns"], 4)
        self.assertEqual(data["frame_count"], 4)
        self.assertEqual(probe(self.video)["width"], 64)


if __name__ == "__main__":
    unittest.main()
