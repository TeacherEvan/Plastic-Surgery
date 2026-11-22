"""Behavioural tests for preflight_video_polish.py."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
AUDITOR = ROOT / "scripts" / "preflight_video_polish.py"
SCHEMA_PATH = ROOT / "schemas" / "video-polish-report.schema.json"

sys.path.insert(0, str(ROOT / "scripts"))
from preflight_video_polish import (  # noqa: E402
    audit_storyboard,
    build_sarif,
    check_mp4_faststart,
)


def _clean_board() -> dict[str, Any]:
    return {
        "meta": {"title": "Polished Board", "seed": 42},
        "format": {"width": 1080, "height": 1920, "fps": 30},
        "style": {
            "preset": "tech_blueprint",
            "grade": {
                "grain": 0.08,
                "vignette": 0.15,
                "halation": 0.15,
                "warmth": -0.05,
            },
        },
        "scenes": [
            {
                "scene_id": "hook_1",
                "archetype": "code_report",
                "duration_sec": 2.5,
                "fade_in_sec": 0.2,
                "camera": {
                    "zoom_start": 1.0,
                    "zoom_end": 1.05,
                    "easing": "ease_out_expo",
                },
                "elements": [
                    {"type": "orb_pulse", "cx": 540, "cy": 800, "radius": 60},
                    {"type": "hud_badge", "x": 200, "y": 400, "text": "LIVE"},
                ],
            }
        ],
    }


class StoryboardPolishTests(unittest.TestCase):
    def _audit(
        self, board: dict[str, Any], safe_mode: str = "strict"
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "board.json"
            p.write_text(json.dumps(board), encoding="utf-8")
            return audit_storyboard(p, safe_mode, "auto")

    def test_clean_board_scores_100_and_matches_schema(self) -> None:
        res = self._audit(_clean_board())
        self.assertEqual(res["defects_count"], 0)
        self.assertEqual(res["video_health_score"], 100)
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(instance=res, schema=schema)

    def test_linear_easing_and_off_canvas_and_safe_zone(self) -> None:
        board = _clean_board()
        board["scenes"][0]["camera"]["easing"] = "linear"
        board["scenes"][0]["elements"] = [
            {"type": "orb_pulse", "cx": 1200, "cy": 800, "radius": 40},
            {"type": "hud_badge", "x": 100, "y": 100, "text": "TOP"},
        ]
        codes = [d["code"] for d in self._audit(board)["defects"]]
        self.assertIn("STORYBOARD_LINEAR_EASING", codes)
        self.assertIn("STORYBOARD_OFF_CANVAS_ELEMENT", codes)
        self.assertIn("STORYBOARD_SAFE_ZONE_BREACH", codes)

    def test_low_contrast_preset_and_unattributed_image(self) -> None:
        board = _clean_board()
        board["style"] = {"preset": "punchy_pop"}
        board["scenes"][0]["elements"].append({"type": "image", "path": "a.jpg"})
        codes = [d["code"] for d in self._audit(board)["defects"]]
        self.assertIn("STORYBOARD_LOW_CONTRAST_PALETTE", codes)
        self.assertIn("STORYBOARD_UNATTRIBUTED_MEDIA", codes)

    def test_3d_script_traversal_blocked_and_hazard_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            local_mjs = Path(td) / "custom.mjs"
            local_mjs.write_text(
                "renderer.shadowMap.type = THREE.PCFSoftShadowMap;", encoding="utf-8"
            )
            board = _clean_board()
            board["scenes"] = [
                {
                    "scene_id": "s1",
                    "archetype": "mixed",
                    "backend": "threejs_3d",
                    "duration_sec": 2.0,
                    "scene_spec": {
                        "category": "network_topology_3d",
                        "params": {"threejs_script": "../../evil.mjs"},
                    },
                },
                {
                    "scene_id": "s2",
                    "archetype": "mixed",
                    "backend": "threejs_3d",
                    "duration_sec": 2.0,
                    "scene_spec": {
                        "category": "network_topology_3d",
                        "params": {"threejs_script": "custom.mjs"},
                    },
                },
            ]
            p = Path(td) / "board.json"
            p.write_text(json.dumps(board), encoding="utf-8")
            codes = [
                d["code"] for d in audit_storyboard(p, "strict", "auto")["defects"]
            ]
            self.assertIn("STORYBOARD_UNSAFE_ASSET_PATH", codes)
            self.assertIn("STORYBOARD_THREEJS_SCRIPT_DEFECT", codes)


class Mp4FaststartAndCliTests(unittest.TestCase):
    def test_faststart_atom_walker(self) -> None:
        def atom(tag: bytes, payload_len: int) -> bytes:
            return struct.pack(">I4s", 8 + payload_len, tag) + b"\x00" * payload_len

        with tempfile.TemporaryDirectory() as td:
            good = Path(td) / "good.mp4"
            good.write_bytes(atom(b"ftyp", 4) + atom(b"moov", 4) + atom(b"mdat", 8))
            self.assertIs(check_mp4_faststart(good), True)

            bad = Path(td) / "bad.mp4"
            bad.write_bytes(atom(b"ftyp", 4) + atom(b"mdat", 8) + atom(b"moov", 4))
            self.assertIs(check_mp4_faststart(bad), False)

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "ffmpeg/ffprobe required for MP4 integration test",
    )
    def test_ffmpeg_good_and_bad_mp4_audit_and_sarif(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            good_mp4 = Path(td) / "good.mp4"
            bad_mp4 = Path(td) / "bad.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=320x240:r=30:d=1",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=1",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-colorspace",
                    "bt709",
                    "-color_primaries",
                    "bt709",
                    "-color_trc",
                    "bt709",
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-movflags",
                    "+faststart",
                    str(good_mp4),
                ],
                check=True,
                capture_output=True,
            )
            r_good = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AUDITOR),
                    str(good_mp4),
                    "--json",
                    "--fail-on",
                    "high",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r_good.returncode, 0, r_good.stdout + r_good.stderr)
            payload = json.loads(r_good.stdout)
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.validate(instance=payload, schema=schema)

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=320x240:r=30:d=1",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=44100:duration=1",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv444p",
                    "-c:a",
                    "aac",
                    "-ar",
                    "44100",
                    str(bad_mp4),
                ],
                check=True,
                capture_output=True,
            )
            r_bad = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AUDITOR),
                    str(bad_mp4),
                    "--json",
                    "--fail-on",
                    "high",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r_bad.returncode, 1)
            bad_codes = [d["code"] for d in json.loads(r_bad.stdout)["defects"]]
            self.assertIn("VIDEO_INVALID_PIX_FMT", bad_codes)
            self.assertIn("VIDEO_MISSING_BT709_TAGS", bad_codes)
            self.assertIn("VIDEO_AUDIO_FORMAT_MISMATCH", bad_codes)
            sarif = build_sarif(json.loads(r_bad.stdout))
            self.assertEqual(sarif["version"], "2.1.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
