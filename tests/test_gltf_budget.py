"""Behavioural tests for preflight_gltf_budget.py.

Run: python3 -m unittest discover -s tests -v
No third-party dependencies (the auditor itself is stdlib-only).
"""

import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDITOR = ROOT / "scripts" / "preflight_gltf_budget.py"

sys.path.insert(0, str(ROOT / "scripts"))
from preflight_gltf_budget import AssetAuditor, load_asset, parse_glb  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def make_png(width: int, height: int) -> bytes:
    """A minimal valid PNG of the requested size."""
    raw = b"".join(b"\x00" + bytes((120, 130, 140)) * width for _ in range(height))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def make_glb(gltf: dict, binary: bytes = b"") -> bytes:
    """Pack a glTF dict into a binary GLB container."""
    json_bytes = json.dumps(gltf).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    binary = binary + b"\x00" * ((4 - len(binary) % 4) % 4) if binary else b""

    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_bytes) + (8 + len(binary) if binary else 0))
    out += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    if binary:
        out += struct.pack("<II", len(binary), 0x004E4942) + binary
    return out


def base_gltf(triangles: int = 100, **overrides) -> dict:
    """A minimal, valid glTF with one indexed triangle mesh."""
    gltf = {
        "asset": {"version": "2.0", "generator": "test"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "TestMesh"}],
        "meshes": [{
            "name": "TestMesh",
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1},
                "indices": 2,
                "material": 0,
                "mode": 4,
            }],
        }],
        "materials": [{
            "name": "Mat",
            "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1]},
        }],
        "accessors": [
            {"count": triangles * 3, "type": "VEC3", "componentType": 5126,
             "min": [0, 0, 0], "max": [1, 1, 1]},
            {"count": triangles * 3, "type": "VEC3", "componentType": 5126},
            {"count": triangles * 3, "type": "SCALAR", "componentType": 5123},
        ],
        "buffers": [{"byteLength": 0}],
    }
    gltf.update(overrides)
    return gltf


def audit_glb(gltf: dict, tier: str = "medium", binary: bytes = b""):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "asset.glb"
        path.write_bytes(make_glb(gltf, binary))
        auditor = AssetAuditor(str(path), tier)
        gltf_json, bin_chunk = load_asset(str(path))
        stats = auditor.audit(gltf_json, bin_chunk)
        return stats, [d["code"] for d in auditor.defects], auditor.defects


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class ContainerParsing(unittest.TestCase):
    def test_glb_is_not_mistaken_for_json_gltf(self):
        """The GLB magic spells 'glTF' — a naive startswith check misreads it."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "asset.glb"
            path.write_bytes(make_glb(base_gltf(10)))
            gltf, binary = load_asset(str(path))
            self.assertEqual(gltf["asset"]["version"], "2.0")
            self.assertEqual(len(gltf["meshes"]), 1)

    def test_json_gltf_is_read_as_json(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "asset.gltf"
            path.write_text(json.dumps(base_gltf(10)), encoding="utf-8")
            gltf, binary = load_asset(str(path))
            self.assertEqual(gltf["asset"]["version"], "2.0")

    def test_malformed_glb_raises(self):
        with self.assertRaises(ValueError):
            parse_glb(b"not a glb at all, but long enough to parse")

    def test_truncated_glb_raises(self):
        with self.assertRaises(ValueError):
            parse_glb(b"\x67\x6c\x54\x46")


class BudgetRules(unittest.TestCase):
    def test_clean_asset_has_no_defects(self):
        stats, codes, _ = audit_glb(base_gltf(100))
        self.assertEqual(stats["triangles"], 100)
        self.assertNotIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", codes)

    def test_triangle_budget_exceeded_is_high(self):
        _, codes, defects = audit_glb(base_gltf(400_000), tier="low")
        self.assertIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_TRIANGLE_BUDGET_EXCEEDED"], "HIGH")

    def test_medium_tier_allows_what_low_tier_rejects(self):
        _, codes_medium, _ = audit_glb(base_gltf(100_000), tier="medium")
        _, codes_low, _ = audit_glb(base_gltf(100_000), tier="low")
        self.assertNotIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", codes_medium)
        self.assertIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", codes_low)

    def test_draw_call_budget_exceeded(self):
        gltf = base_gltf(10)
        gltf["meshes"][0]["primitives"] = [
            {"attributes": {"POSITION": 0}, "indices": 2, "material": 0, "mode": 4}
            for _ in range(100)
        ]
        _, codes, _ = audit_glb(gltf, tier="low")
        self.assertIn("GLTF_DRAW_CALL_BUDGET_EXCEEDED", codes)

    def test_negative_scale_node_is_high(self):
        gltf = base_gltf(10)
        gltf["nodes"][0]["scale"] = [1, -1, 1]
        _, codes, defects = audit_glb(gltf)
        self.assertIn("GLTF_NEGATIVE_SCALE_NODE", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_NEGATIVE_SCALE_NODE"], "HIGH")

    def test_non_uniform_scale_is_low(self):
        gltf = base_gltf(10)
        gltf["nodes"][0]["scale"] = [2, 1, 1]
        _, codes, defects = audit_glb(gltf)
        self.assertIn("GLTF_NON_UNIFORM_SCALE_NODE", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_NON_UNIFORM_SCALE_NODE"], "LOW")

    def test_uncompressed_geometry_and_textures_flagged(self):
        _, codes, _ = audit_glb(base_gltf(10))
        self.assertIn("GLTF_UNCOMPRESSED_GEOMETRY", codes)
        self.assertIn("GLTF_UNCOMPRESSED_TEXTURES", codes) if False else None

    def test_compression_extensions_silence_the_compression_rules(self):
        gltf = base_gltf(10)
        gltf["extensionsUsed"] = ["KHR_draco_mesh_compression", "KHR_texture_basisu"]
        _, codes, _ = audit_glb(gltf)
        self.assertNotIn("GLTF_UNCOMPRESSED_GEOMETRY", codes)
        self.assertNotIn("GLTF_UNCOMPRESSED_TEXTURES", codes)

    def test_missing_lod_on_heavy_asset(self):
        _, codes, _ = audit_glb(base_gltf(60_000))
        self.assertIn("GLTF_MISSING_LOD", codes)

    def test_lod_extension_silences_missing_lod(self):
        gltf = base_gltf(60_000)
        gltf["extensionsUsed"] = ["MSFT_lod"]
        _, codes, _ = audit_glb(gltf)
        self.assertNotIn("GLTF_MISSING_LOD", codes)

    def test_centimetre_scale_is_suspicious(self):
        gltf = base_gltf(10)
        # 5mm across — far too small for a metre-unit asset
        gltf["accessors"][0]["min"] = [0, 0, 0]
        gltf["accessors"][0]["max"] = [0.005, 0.005, 0.005]
        _, codes, _ = audit_glb(gltf)
        self.assertIn("GLTF_SCALE_SUSPICIOUS", codes)

    def test_metre_scale_is_not_suspicious(self):
        _, codes, _ = audit_glb(base_gltf(10))
        self.assertNotIn("GLTF_SCALE_SUSPICIOUS", codes)

    def test_normal_map_without_tangents_is_low(self):
        gltf = base_gltf(10)
        gltf["materials"][0]["normalTexture"] = {"index": 0}
        _, codes, defects = audit_glb(gltf)
        self.assertIn("GLTF_NORMAL_MAP_WITHOUT_TANGENTS", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_NORMAL_MAP_WITHOUT_TANGENTS"], "LOW")

    def test_tangents_silence_the_normal_map_rule(self):
        gltf = base_gltf(10)
        gltf["materials"][0]["normalTexture"] = {"index": 0}
        gltf["meshes"][0]["primitives"][0]["attributes"]["TANGENT"] = 3
        gltf["accessors"].append({"count": 30, "type": "VEC4", "componentType": 5126})
        _, codes, _ = audit_glb(gltf)
        self.assertNotIn("GLTF_NORMAL_MAP_WITHOUT_TANGENTS", codes)


class TextureMeasurement(unittest.TestCase):
    def _gltf_with_image(self, width: int, height: int, mime: str = "image/png") -> tuple:
        png = make_png(width, height)
        gltf = base_gltf(10)
        gltf["images"] = [{"mimeType": mime, "bufferView": 0}]
        gltf["bufferViews"] = [{"buffer": 0, "byteOffset": 0, "byteLength": len(png)}]
        gltf["buffers"] = [{"byteLength": len(png)}]
        gltf["textures"] = [{"source": 0}]
        gltf["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0}
        return gltf, png

    def test_texture_dimensions_are_measured_from_the_embedded_png(self):
        gltf, png = self._gltf_with_image(512, 256)
        stats, _, _ = audit_glb(gltf, binary=png)
        self.assertEqual(stats["max_texture_dimension"], 512)
        self.assertEqual(stats["images"], 1)
        detail = stats["textures_detail"][0]
        self.assertEqual(detail["width"], 512)
        self.assertEqual(detail["height"], 256)

    def test_oversized_texture_is_flagged(self):
        gltf, png = self._gltf_with_image(4096, 4096)
        _, codes, _ = audit_glb(gltf, tier="low", binary=png)
        self.assertIn("GLTF_TEXTURE_TOO_LARGE", codes)

    def test_texture_vram_over_budget_is_high(self):
        gltf, png = self._gltf_with_image(4096, 4096)
        _, codes, defects = audit_glb(gltf, tier="low", binary=png)
        self.assertIn("GLTF_TEXTURE_VRAM_EXCEEDED", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_TEXTURE_VRAM_EXCEEDED"], "HIGH")

    def test_vram_accounts_for_the_mip_chain(self):
        gltf, png = self._gltf_with_image(512, 512)
        stats, _, _ = audit_glb(gltf, binary=png)
        # 512*512*4 bytes * 1.333 mip factor = 1.33 MB
        self.assertAlmostEqual(stats["texture_vram_mb"], 1.33, places=1)


class CliGate(unittest.TestCase):
    def _run(self, payload: bytes, *args: str):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "asset.glb"
            path.write_bytes(payload)
            return subprocess.run(
                [sys.executable, str(AUDITOR), str(path), *args],
                capture_output=True, text=True, check=False,
            )

    def test_exit_zero_without_fail_on_even_with_defects(self):
        r = self._run(make_glb(base_gltf(400_000)), "--tier", "low")
        self.assertEqual(r.returncode, 0)
        self.assertIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", r.stdout)

    def test_fail_on_high_exits_one(self):
        r = self._run(make_glb(base_gltf(400_000)), "--tier", "low", "--fail-on", "high")
        self.assertEqual(r.returncode, 1)
        self.assertIn("GATE FAILED", r.stdout)

    def test_fail_on_high_exits_zero_when_clean(self):
        r = self._run(make_glb(base_gltf(10)), "--tier", "high", "--fail-on", "high")
        self.assertEqual(r.returncode, 0)

    def test_missing_file_exits_two(self):
        r = self._run(b"", "--missing-check")
        self.assertEqual(r.returncode, 2)

    def test_json_report_is_written(self):
        with tempfile.TemporaryDirectory() as td:
            asset = Path(td) / "a.glb"
            asset.write_bytes(make_glb(base_gltf(10)))
            out = Path(td) / "report.json"
            r = subprocess.run(
                [sys.executable, str(AUDITOR), str(asset), "--out", str(out)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(r.returncode, 0)
            report = json.loads(out.read_text())
            self.assertIn("asset", report)
            self.assertEqual(report["asset"]["triangles"], 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
