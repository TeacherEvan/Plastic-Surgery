"""Behavioural tests for polish_surgical_media.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
POLISHER = ROOT / "scripts" / "polish_surgical_media.py"
ACTION_SCHEMA = ROOT / "schemas" / "video-polish-action.schema.json"

sys.path.insert(0, str(ROOT / "scripts"))
from polish_surgical_media import immutable_fingerprint, repair_contrast_hex  # noqa: E402
from preflight_video_polish import wcag_contrast_ratio  # noqa: E402


def _dirty_board() -> dict[str, Any]:
    return {
        "meta": {"title": "Dirty Board", "seed": 123},
        "format": {"width": 1080, "height": 1920, "fps": 30},
        "style": {"preset": "punchy_pop"},
        "scenes": [
            {
                "scene_id": "s1",
                "archetype": "mixed",
                "duration_sec": 2.5,
                "narration": "Immutable narration.",
                "words": [{"word": "Immutable", "start": 0.0, "end": 0.5}],
                "camera": {"zoom_start": 1.0, "zoom_end": 1.04, "easing": "linear"},
                "elements": [
                    {"type": "orb_pulse", "cx": 1500, "cy": 800, "radius": 50},
                    {"type": "hud_badge", "x": 10, "y": 10, "text": "TOP"},
                    {
                        "type": "image",
                        "src": "a.jpg",
                        "attribution": "CC0",
                        "attribution_y": 1850,
                    },
                ],
            },
            {
                "scene_id": "s2",
                "archetype": "doc_essay",
                "duration_sec": 2.5,
                "elements": [{"type": "background", "color": "#0B0E18"}],
            },
        ],
    }


class PolishSurgicalMediaTests(unittest.TestCase):
    def test_repair_contrast_hex_achieves_wcag_aa(self) -> None:
        fixed = repair_contrast_hex("#FF4D6D", "#FFF4D6", 4.5)
        self.assertGreaterEqual(wcag_contrast_ratio(fixed, "#FFF4D6"), 4.5)

    def test_refuses_in_place_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "b.json"
            p.write_text(json.dumps(_dirty_board()), encoding="utf-8")
            r = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(POLISHER),
                    "storyboard",
                    "--in",
                    str(p),
                    "--out",
                    str(p),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 2)

    def test_mode_a_storyboard_polish_and_immutable_sha(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / "in.json"
            out = Path(td) / "out.json"
            rep = Path(td) / "report.json"
            raw = _dirty_board()
            inp.write_text(json.dumps(raw), encoding="utf-8")
            before_sha = immutable_fingerprint(raw)

            r = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(POLISHER),
                    "storyboard",
                    "--in",
                    str(inp),
                    "--out",
                    str(out),
                    "--look",
                    "preserve",
                    "--report",
                    str(rep),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            report = json.loads(rep.read_text(encoding="utf-8"))
            schema = json.loads(ACTION_SCHEMA.read_text(encoding="utf-8"))
            jsonschema.validate(instance=report, schema=schema)
            self.assertTrue(report["immutable_verified"])
            self.assertEqual(report["immutable_sha256_before"], before_sha)
            self.assertEqual(report["immutable_sha256_after"], before_sha)
            self.assertEqual(report["after_score"], 100)

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "ffmpeg/ffprobe required for Mode B video polish test",
    )
    def test_mode_b_video_polish_loudnorm_and_qc_frames(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.mp4"
            out = Path(td) / "polished.mp4"
            qc_dir = Path(td) / "qc"
            rep = Path(td) / "action.json"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=320x240:rate=30:duration=2",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=44100:duration=2",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv444p",
                    "-c:a",
                    "aac",
                    "-ar",
                    "44100",
                    str(bad),
                ],
                check=True,
                capture_output=True,
            )
            r = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(POLISHER),
                    "video",
                    "--in",
                    str(bad),
                    "--out",
                    str(out),
                    "--look",
                    "cinematic_clean",
                    "--loudnorm",
                    "--qc-frames",
                    str(qc_dir),
                    "--report",
                    str(rep),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            report = json.loads(rep.read_text(encoding="utf-8"))
            schema = json.loads(ACTION_SCHEMA.read_text(encoding="utf-8"))
            jsonschema.validate(instance=report, schema=schema)
            self.assertEqual(report["after_score"], 100)
            self.assertEqual(len(report["qc_frames"]), 6)
            for png in report["qc_frames"]:
                self.assertTrue(Path(png).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
