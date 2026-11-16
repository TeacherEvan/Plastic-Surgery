"""Behavioural tests for preflight_gltf_budget.py.

Run: pytest -v tests/test_gltf_budget.py
"""

from __future__ import annotations

import base64
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
AUDITOR = ROOT / "scripts" / "preflight_gltf_budget.py"
SCHEMA_PATH = ROOT / "schemas" / "gltf-budget-report.schema.json"

sys.path.insert(0, str(ROOT / "scripts"))
from preflight_gltf_budget import (  # noqa: E402
    AssetAuditor,
    decode_data_uri,
    jpeg_size,
    load_asset,
    parse_glb,
    webp_size,
)


def make_png(width: int, height: int) -> bytes:
    """Create a minimal valid PNG of the requested size."""
    raw = b"".join(b"\x00" + bytes((120, 130, 140)) * width for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def make_ktx2(width: int, height: int) -> bytes:
    """Create a minimal valid 80-byte KTX2 header."""
    ident = b"\xabKTX 20\xbb\r\n\x1a\n"
    fields = struct.pack("<IIII", 0, 1, width, height)
    return ident + fields + b"\x00" * (80 - len(ident) - len(fields))


def make_jpeg_sof0(width: int, height: int, with_fill: bool = False) -> bytes:
    """Create a minimal JPEG stream containing a SOF0 segment."""
    prefix = b"\xff\xd8\xff\xff\xe0\x00\x04\x00\x00" if with_fill else b"\xff\xd8"
    sof0 = b"\xff\xc0" + struct.pack(">HBHHB", 8, 8, height, width, 3) + b"\x00" * 3
    return prefix + sof0 + b"\xff\xd9"


def make_webp_vp8(width: int, height: int) -> bytes:
    payload = b"\x00" * 3 + b"\x9d\x01\x2a" + struct.pack("<HH", width, height)
    return (
        b"RIFF"
        + struct.pack("<I", 22)
        + b"WEBP"
        + b"VP8 "
        + struct.pack("<I", 10)
        + payload
    )


def make_webp_vp8l(width: int, height: int) -> bytes:
    bits = ((width - 1) & 0x3FFF) | (((height - 1) & 0x3FFF) << 14)
    return (
        b"RIFF"
        + struct.pack("<I", 17)
        + b"WEBP"
        + b"VP8L"
        + struct.pack("<I", 5)
        + b"\x2f"
        + struct.pack("<I", bits)
    )


def make_webp_vp8x(width: int, height: int) -> bytes:
    w_m1 = (width - 1).to_bytes(3, "little")
    h_m1 = (height - 1).to_bytes(3, "little")
    return (
        b"RIFF"
        + struct.pack("<I", 22)
        + b"WEBP"
        + b"VP8X"
        + struct.pack("<I", 10)
        + b"\x00\x00\x00\x00"
        + w_m1
        + h_m1
    )


def make_glb(gltf: dict[str, Any], binary: bytes = b"") -> bytes:
    """Pack a glTF dict into a binary GLB container."""
    json_bytes = json.dumps(gltf).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    padded_bin = binary + b"\x00" * ((4 - len(binary) % 4) % 4) if binary else b""

    total_len = 12 + 8 + len(json_bytes) + (8 + len(padded_bin) if padded_bin else 0)
    out = struct.pack("<III", 0x46546C67, 2, total_len)
    out += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    if padded_bin:
        out += struct.pack("<II", len(padded_bin), 0x004E4942) + padded_bin
    return out


def base_gltf(triangles: int = 100, **overrides: Any) -> dict[str, Any]:
    """Build a minimal valid glTF with one indexed triangle mesh."""
    gltf: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "test"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "TestMesh"}],
        "meshes": [
            {
                "name": "TestMesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1},
                        "indices": 2,
                        "material": 0,
                        "mode": 4,
                    }
                ],
            }
        ],
        "materials": [
            {
                "name": "Mat",
                "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1]},
            }
        ],
        "accessors": [
            {
                "count": triangles * 3,
                "type": "VEC3",
                "componentType": 5126,
                "min": [0, 0, 0],
                "max": [1, 1, 1],
            },
            {"count": triangles * 3, "type": "VEC3", "componentType": 5126},
            {"count": triangles * 3, "type": "SCALAR", "componentType": 5123},
        ],
        "buffers": [{"byteLength": 0}],
    }
    gltf.update(overrides)
    return gltf


def audit_glb(
    gltf: dict[str, Any], tier: str = "medium", binary: bytes = b""
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "asset.glb"
        path.write_bytes(make_glb(gltf, binary))
        auditor = AssetAuditor(str(path), tier)
        gltf_json, bin_chunk = load_asset(str(path))
        stats: dict[str, Any] = auditor.audit(gltf_json, bin_chunk)
        defects: list[dict[str, Any]] = auditor.defects
        codes: list[str] = [str(d["code"]) for d in defects]
        return stats, codes, defects


class ContainerParsing(unittest.TestCase):
    def test_glb_is_not_mistaken_for_json_gltf(self) -> None:
        """The GLB magic spells 'glTF' — a naive startswith check misreads it."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "asset.glb"
            path.write_bytes(make_glb(base_gltf(10)))
            gltf, _ = load_asset(str(path))
            self.assertEqual(gltf["asset"]["version"], "2.0")
            self.assertEqual(len(gltf["meshes"]), 1)

    def test_json_gltf_is_read_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "asset.gltf"
            path.write_text(json.dumps(base_gltf(10)), encoding="utf-8")
            gltf, _ = load_asset(str(path))
            self.assertEqual(gltf["asset"]["version"], "2.0")

    def test_malformed_glb_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_glb(b"not a glb at all, but long enough to parse")

    def test_truncated_glb_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_glb(b"\x67\x6c\x54\x46")

    def test_truncated_bin_chunk_raises(self) -> None:
        valid_json = json.dumps(base_gltf(10)).encode("utf-8")
        valid_json += b" " * ((4 - len(valid_json) % 4) % 4)
        bad_total = 12 + 8 + len(valid_json) + 8 + 4
        payload = (
            struct.pack("<III", 0x46546C67, 2, bad_total)
            + struct.pack("<II", len(valid_json), 0x4E4F534A)
            + valid_json
            + struct.pack("<II", 512, 0x004E4942)
            + b"\x00\x00\x00\x00"
        )
        with self.assertRaises(ValueError):
            parse_glb(payload)

    def test_data_uri_and_path_traversal_handling(self) -> None:
        png = make_png(64, 64)
        b64_png = base64.b64encode(png).decode("ascii")
        decoded = decode_data_uri(f"data:image/png;base64,{b64_png}")
        self.assertEqual(decoded, png)

        with tempfile.TemporaryDirectory() as td:
            gltf = base_gltf(10)
            gltf["images"] = [
                {"uri": f"data:image/png;base64,{b64_png}"},
                {"uri": "../../etc/passwd"},
            ]
            asset_path = Path(td) / "scene.gltf"
            asset_path.write_text(json.dumps(gltf), encoding="utf-8")
            loaded, bin_chunk = load_asset(str(asset_path))
            auditor = AssetAuditor(str(asset_path), "medium")
            stats = auditor.audit(loaded, bin_chunk)
            codes = [str(d["code"]) for d in auditor.defects]
            self.assertEqual(stats["textures_detail"][0]["width"], 64)
            self.assertIn("GLTF_UNSAFE_EXTERNAL_URI", codes)


class BudgetRules(unittest.TestCase):
    def test_clean_asset_has_no_defects(self) -> None:
        stats, codes, _ = audit_glb(base_gltf(100))
        self.assertEqual(stats["triangles"], 100)
        self.assertNotIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", codes)

    def test_triangle_budget_exceeded_is_high(self) -> None:
        _, codes, defects = audit_glb(base_gltf(400_000), tier="low")
        self.assertIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_TRIANGLE_BUDGET_EXCEEDED"], "HIGH")

    def test_medium_tier_allows_what_low_tier_rejects(self) -> None:
        _, codes_medium, _ = audit_glb(base_gltf(100_000), tier="medium")
        _, codes_low, _ = audit_glb(base_gltf(100_000), tier="low")
        self.assertNotIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", codes_medium)
        self.assertIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", codes_low)

    def test_draw_call_budget_exceeded(self) -> None:
        gltf = base_gltf(10)
        gltf["meshes"][0]["primitives"] = [
            {"attributes": {"POSITION": 0}, "indices": 2, "material": 0, "mode": 4}
            for _ in range(100)
        ]
        _, codes, _ = audit_glb(gltf, tier="low")
        self.assertIn("GLTF_DRAW_CALL_BUDGET_EXCEEDED", codes)

    def test_triangle_strip_and_fan_modes_counted(self) -> None:
        gltf = base_gltf(10)
        gltf["accessors"][2]["count"] = 10
        gltf["meshes"][0]["primitives"][0]["mode"] = 5
        stats_strip, _, _ = audit_glb(gltf)
        self.assertEqual(stats_strip["triangles"], 8)

        gltf["meshes"][0]["primitives"][0]["mode"] = 6
        stats_fan, _, _ = audit_glb(gltf)
        self.assertEqual(stats_fan["triangles"], 8)

    def test_negative_scale_node_is_high(self) -> None:
        gltf = base_gltf(10)
        gltf["nodes"][0]["scale"] = [1, -1, 1]
        _, codes, defects = audit_glb(gltf)
        self.assertIn("GLTF_NEGATIVE_SCALE_NODE", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_NEGATIVE_SCALE_NODE"], "HIGH")

    def test_non_uniform_scale_is_low(self) -> None:
        gltf = base_gltf(10)
        gltf["nodes"][0]["scale"] = [2, 1, 1]
        _, codes, defects = audit_glb(gltf)
        self.assertIn("GLTF_NON_UNIFORM_SCALE_NODE", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_NON_UNIFORM_SCALE_NODE"], "LOW")

    def test_uncompressed_geometry_and_textures_flagged(self) -> None:
        png = make_png(64, 64)
        gltf = base_gltf(10)
        gltf["images"] = [{"mimeType": "image/png", "bufferView": 0}]
        gltf["bufferViews"] = [{"buffer": 0, "byteOffset": 0, "byteLength": len(png)}]
        gltf["buffers"] = [{"byteLength": len(png)}]
        gltf["textures"] = [{"source": 0}]
        _, codes, _ = audit_glb(gltf, binary=png)
        self.assertIn("GLTF_UNCOMPRESSED_GEOMETRY", codes)
        self.assertIn("GLTF_UNCOMPRESSED_TEXTURES", codes)

    def test_compression_extensions_silence_the_compression_rules(self) -> None:
        gltf = base_gltf(10)
        gltf["extensionsUsed"] = ["KHR_draco_mesh_compression", "KHR_texture_basisu"]
        _, codes, _ = audit_glb(gltf)
        self.assertNotIn("GLTF_UNCOMPRESSED_GEOMETRY", codes)
        self.assertNotIn("GLTF_UNCOMPRESSED_TEXTURES", codes)

    def test_missing_lod_on_heavy_asset(self) -> None:
        _, codes, _ = audit_glb(base_gltf(60_000))
        self.assertIn("GLTF_MISSING_LOD", codes)

    def test_lod_extension_silences_missing_lod(self) -> None:
        gltf = base_gltf(60_000)
        gltf["extensionsUsed"] = ["MSFT_lod"]
        _, codes, _ = audit_glb(gltf)
        self.assertNotIn("GLTF_MISSING_LOD", codes)

    def test_centimetre_scale_is_suspicious_even_when_normal_is_accessor_zero(
        self,
    ) -> None:
        gltf = base_gltf(10)
        gltf["accessors"] = [
            {"count": 30, "type": "VEC3", "componentType": 5126},
            {
                "count": 30,
                "type": "VEC3",
                "componentType": 5126,
                "min": [0, 0, 0],
                "max": [0.005, 0.005, 0.005],
            },
            {"count": 30, "type": "SCALAR", "componentType": 5123},
        ]
        gltf["meshes"][0]["primitives"][0]["attributes"] = {
            "NORMAL": 0,
            "POSITION": 1,
        }
        _, codes, _ = audit_glb(gltf)
        self.assertIn("GLTF_SCALE_SUSPICIOUS", codes)

    def test_metre_scale_is_not_suspicious(self) -> None:
        _, codes, _ = audit_glb(base_gltf(10))
        self.assertNotIn("GLTF_SCALE_SUSPICIOUS", codes)

    def test_normal_map_without_tangents_is_low(self) -> None:
        gltf = base_gltf(10)
        gltf["materials"][0]["normalTexture"] = {"index": 0}
        _, codes, defects = audit_glb(gltf)
        self.assertIn("GLTF_NORMAL_MAP_WITHOUT_TANGENTS", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_NORMAL_MAP_WITHOUT_TANGENTS"], "LOW")

    def test_tangents_silence_the_normal_map_rule(self) -> None:
        gltf = base_gltf(10)
        gltf["materials"][0]["normalTexture"] = {"index": 0}
        gltf["meshes"][0]["primitives"][0]["attributes"]["TANGENT"] = 3
        gltf["accessors"].append({"count": 30, "type": "VEC4", "componentType": 5126})
        _, codes, _ = audit_glb(gltf)
        self.assertNotIn("GLTF_NORMAL_MAP_WITHOUT_TANGENTS", codes)

    def test_material_slot_explosion_and_missing_material_vs_index_zero(self) -> None:
        gltf = base_gltf(10)
        gltf["materials"] = [
            {"name": f"Mat{i}", "pbrMetallicRoughness": {}} for i in range(18)
        ]
        _, codes, _ = audit_glb(gltf, tier="low")
        self.assertIn("GLTF_MATERIAL_SLOT_EXPLOSION", codes)
        self.assertNotIn("GLTF_PRIMITIVE_WITHOUT_MATERIAL", codes)

        del gltf["meshes"][0]["primitives"][0]["material"]
        _, codes_missing, _ = audit_glb(gltf, tier="medium")
        self.assertIn("GLTF_PRIMITIVE_WITHOUT_MATERIAL", codes_missing)


class TextureMeasurement(unittest.TestCase):
    def _gltf_with_bytes(
        self, img_bytes: bytes, mime: str
    ) -> tuple[dict[str, Any], bytes]:
        gltf = base_gltf(10)
        gltf["images"] = [{"mimeType": mime, "bufferView": 0}]
        gltf["bufferViews"] = [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(img_bytes)}
        ]
        gltf["buffers"] = [{"byteLength": len(img_bytes)}]
        gltf["textures"] = [{"source": 0}]
        gltf["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0}
        return gltf, img_bytes

    def _gltf_with_image(
        self, width: int, height: int, mime: str = "image/png"
    ) -> tuple[dict[str, Any], bytes]:
        return self._gltf_with_bytes(make_png(width, height), mime)

    def test_texture_dimensions_are_measured_from_the_embedded_png(self) -> None:
        gltf, png = self._gltf_with_image(512, 256)
        stats, _, _ = audit_glb(gltf, binary=png)
        self.assertEqual(stats["max_texture_dimension"], 512)
        self.assertEqual(stats["images"], 1)
        detail = stats["textures_detail"][0]
        self.assertEqual(detail["width"], 512)
        self.assertEqual(detail["height"], 256)

    def test_oversized_texture_is_flagged(self) -> None:
        gltf, png = self._gltf_with_image(4096, 4096)
        _, codes, _ = audit_glb(gltf, tier="low", binary=png)
        self.assertIn("GLTF_TEXTURE_TOO_LARGE", codes)

    def test_texture_vram_over_budget_is_high(self) -> None:
        gltf, png = self._gltf_with_image(4096, 4096)
        _, codes, defects = audit_glb(gltf, tier="low", binary=png)
        self.assertIn("GLTF_TEXTURE_VRAM_EXCEEDED", codes)
        sev = {d["code"]: d["severity"] for d in defects}
        self.assertEqual(sev["GLTF_TEXTURE_VRAM_EXCEEDED"], "HIGH")

    def test_vram_accounts_for_the_mip_chain(self) -> None:
        gltf, png = self._gltf_with_image(512, 512)
        stats, _, _ = audit_glb(gltf, binary=png)
        # 512*512*4 bytes * 1.333 mip factor = 1.33 MB
        self.assertAlmostEqual(stats["texture_vram_mb"], 1.33, places=1)

    def test_ktx2_uses_compressed_mip_vram_estimate(self) -> None:
        gltf, ktx = self._gltf_with_bytes(make_ktx2(512, 512), "image/ktx2")
        stats, _, _ = audit_glb(gltf, binary=ktx)
        self.assertEqual(stats["textures_detail"][0]["format"], "image/ktx2")
        self.assertAlmostEqual(stats["texture_vram_mb"], 0.33, places=1)

    def test_jpeg_and_webp_probes(self) -> None:
        self.assertEqual(
            jpeg_size(make_jpeg_sof0(640, 480, with_fill=True)), (640, 480)
        )
        self.assertEqual(webp_size(make_webp_vp8(320, 240)), (320, 240))
        self.assertEqual(webp_size(make_webp_vp8l(128, 96)), (128, 96))
        self.assertEqual(webp_size(make_webp_vp8x(1024, 512)), (1024, 512))


class CliGate(unittest.TestCase):
    def _run(self, payload: bytes, *args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "asset.glb"
            path.write_bytes(payload)
            return subprocess.run(
                [sys.executable, "-B", str(AUDITOR), str(path), *args],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_exit_zero_without_fail_on_even_with_defects(self) -> None:
        r = self._run(make_glb(base_gltf(400_000)), "--tier", "low")
        self.assertEqual(r.returncode, 0)
        self.assertIn("GLTF_TRIANGLE_BUDGET_EXCEEDED", r.stdout)

    def test_fail_on_high_medium_low(self) -> None:
        r_high = self._run(
            make_glb(base_gltf(400_000)), "--tier", "low", "--fail-on", "high"
        )
        self.assertEqual(r_high.returncode, 1)
        self.assertIn("GATE FAILED", r_high.stdout)

        r_med = self._run(make_glb(base_gltf(10)), "--fail-on", "medium")
        self.assertEqual(r_med.returncode, 1)

    def test_fail_on_high_exits_zero_when_clean(self) -> None:
        r = self._run(make_glb(base_gltf(10)), "--tier", "high", "--fail-on", "high")
        self.assertEqual(r.returncode, 0)

    def test_missing_file_exits_two(self) -> None:
        tmp = tempfile.mkdtemp()
        shutil.rmtree(tmp)
        r = subprocess.run(
            [sys.executable, "-B", str(AUDITOR), f"{tmp}/missing.glb"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 2)

    def test_json_report_written_and_stdout_json_matches_schema(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            asset = Path(td) / "a.glb"
            asset.write_bytes(make_glb(base_gltf(10)))
            out = Path(td) / "report.json"
            r = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AUDITOR),
                    str(asset),
                    "--json",
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0)
            stdout_report = json.loads(r.stdout)
            file_report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(stdout_report["asset"]["triangles"], 10)
            self.assertEqual(stdout_report, file_report)
            jsonschema.validate(instance=stdout_report, schema=schema)


if __name__ == "__main__":
    unittest.main(verbosity=2)
