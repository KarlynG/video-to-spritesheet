"""Exercise engine exports with real video extraction and nontrivial page geometry."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
from video_to_spritesheet import ConversionError, Options, convert, validate_manifest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from create_demo import create_video


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg and FFprobe required")
class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="engine exports ")
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / "robot.mp4"
        create_video(cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=self.root)
        self.output = Path(self.work.name) / "export"

    def tearDown(self):
        self.work.cleanup()

    def export(self, engine):
        return convert(self.source, self.output, Options(
            format=engine, frame_count=7, columns=2, rows=2, frame_width=32, frame_height=48,
            padding=2, spacing=3, key_color="00B140", pivot_x=0.25, pivot_y=0.125, pixels_per_unit=32,
            preview=False))

    def test_unity_coordinates_scale_and_multipage(self):
        result = self.export("unity")
        data = json.loads((self.output / "unity.json").read_text())
        self.assertEqual(data["pages"], [
            {"image": "sheet-001.png", "width": 75, "height": 107},
            {"image": "sheet-002.png", "width": 75, "height": 107}])
        self.assertEqual(data["frames"][0]["rect"], {"x": 2, "y": 57, "w": 32, "h": 48})
        self.assertEqual(data["frames"][2]["rect"], {"x": 2, "y": 2, "w": 32, "h": 48})
        self.assertEqual(data["frames"][4]["rect"], data["frames"][0]["rect"])
        self.assertEqual(data["frames"][4]["page"], 1)
        self.assertEqual(data["pivot"], {"x": 0.25, "y": 0.125})
        self.assertEqual(data["pixels_per_unit"], 32)
        self.assertEqual(data["frame_rate"], 3.5)
        self.assertEqual([f["name"] for f in data["frames"]], [f"frame_{i:06}" for i in range(7)])
        # A bottom-origin consumer reads the same content without flipping the PNG.
        with Image.open(self.output / "sheet-001.png") as image:
            rect = data["frames"][0]["rect"]
            top = image.height - rect["y"] - rect["h"]
            cell = image.crop((rect["x"], top, rect["x"] + rect["w"], top + rect["h"]))
            self.assertIsNotNone(cell.getbbox())
            self.assertEqual(cell.getpixel((0, 0))[3], 0)
        self.assertFalse(result["engine_export"]["editor_playback_verified"])
        self.assertTrue((self.output / "VideoToSpriteSheetImporter.cs").is_file())
        self.assertTrue(validate_manifest(self.output / "manifest.json")["valid"])
        data["frames"][0]["rect"]["y"] = 2
        (self.output / "unity.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(ConversionError, "Unity import data"):
            validate_manifest(self.output / "manifest.json")

    def test_paper2d_descriptor_pivots_and_pages(self):
        result = self.export("unreal-paper2d")
        self.assertEqual(len(result["pages"]), 2)
        for index, page in enumerate(result["pages"]):
            self.assertEqual(page["atlas"], f"atlas-{index + 1:03}.paper2dsprites")
            atlas = json.loads((self.output / page["atlas"]).read_text())
            self.assertEqual(atlas["meta"]["image"], page["image"])
            self.assertEqual(atlas["meta"]["size"], {"w": 75, "h": 107})
            frames = [f for f in result["frames"] if f["page"] == index]
            self.assertEqual(list(atlas["frames"]), [f["name"] for f in frames])
            for frame in frames:
                entry = atlas["frames"][frame["name"]]
                self.assertEqual(entry["frame"], frame["rect"])
                self.assertEqual(entry["pivot"], {"x": 0.25, "y": 0.875})
                self.assertEqual(entry["sourceSize"], {"w": 32, "h": 48})
                self.assertFalse(entry["rotated"])
                self.assertFalse(entry["trimmed"])
        self.assertTrue(validate_manifest(self.output / "manifest.json")["valid"])
        atlas["frames"][frames[0]["name"]]["pivot"]["y"] = 0.125
        (self.output / result["pages"][-1]["atlas"]).write_text(json.dumps(atlas))
        with self.assertRaisesRegex(ConversionError, "Paper2D pivot"):
            validate_manifest(self.output / "manifest.json")

    @unittest.skipUnless(shutil.which("node"), "Node.js required for ES module execution")
    def test_phaser_helper_loads_every_page_and_orders_animation(self):
        self.export("phaser")
        script = '''import {preloadVideoSprites, createVideoAnimation} from './phaser.mjs';
const loads = [];
const scene = {load: {atlas: (...args) => loads.push(args)}, anims: {create: args => args}};
preloadVideoSprites(scene, 'assets/knight/', 'knight');
console.log(JSON.stringify({loads, loop: createVideoAnimation(scene, 'run', 'knight'),
                           once: createVideoAnimation(scene, 'run-once', 'knight', 0)}));
'''
        (self.output / "check.mjs").write_text(script)
        run = subprocess.run([shutil.which("node"), str(self.output / "check.mjs")], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout)
        self.assertEqual(data["loads"], [
            ["knight_p0", "assets/knight/sheet-001.png", "assets/knight/atlas-001.json"],
            ["knight_p1", "assets/knight/sheet-002.png", "assets/knight/atlas-002.json"]])
        self.assertEqual(data["loop"]["frames"], [
            {"key": f"knight_p{i // 4}", "frame": f"frame_{i:06}"} for i in range(7)])
        self.assertEqual(data["loop"]["frameRate"], 3.5)
        self.assertEqual(data["loop"]["repeat"], -1)
        self.assertEqual(data["once"]["repeat"], 0)
        self.assertTrue(validate_manifest(self.output / "manifest.json")["valid"])
        (self.output / "phaser.mjs").write_text("export const broken = true;")
        with self.assertRaisesRegex(ConversionError, "Phaser module"):
            validate_manifest(self.output / "manifest.json")

    def test_engine_export_requires_import_files(self):
        self.export("unity")
        (self.output / "VideoToSpriteSheetImporter.cs").unlink()
        with self.assertRaisesRegex(ConversionError, "Missing engine import file"):
            validate_manifest(self.output / "manifest.json")


if __name__ == "__main__":
    unittest.main()
