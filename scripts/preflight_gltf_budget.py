#!/usr/bin/env python3
"""
preflight_gltf_budget.py — Zero-mutation glTF 2.0 / GLB asset budget auditor.

Inspects an authored 3D asset against the Plastic Surgery render budgets:
triangle counts, draw calls, texture VRAM, material slots, texture dimensions,
LOD coverage and compression coverage — then reports what the asset will cost
at runtime.

Usage:
    python3 scripts/preflight_gltf_budget.py asset.glb [--tier medium] [--json] [--out report.json] [--fail-on high]

Supports:
    * .glb  — binary glTF (JSON chunk + BIN chunk)
    * .gltf — JSON glTF with external or data: URI resources

Stdlib only. All operations are strictly read-only.

Tier budgets (see references/threejs_3d_asset_pipeline.md §2, Stage 1):

    tier      triangles   draw calls   texture VRAM   max texture   materials
    low           60 k          80          64 MB        1024          16
    medium       300 k         250         256 MB        2048          32
    high        1.5 M        1000         512 MB        4096          64
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import struct
import sys
import urllib.parse
from pathlib import Path
from typing import Any

LINTER_VERSION = "1.4.0"

TIERS: dict[str, dict[str, int]] = {
    "low": {
        "triangles": 60_000,
        "draw_calls": 80,
        "texture_vram_mb": 64,
        "max_texture": 1024,
        "materials": 16,
    },
    "medium": {
        "triangles": 300_000,
        "draw_calls": 250,
        "texture_vram_mb": 256,
        "max_texture": 2048,
        "materials": 32,
    },
    "high": {
        "triangles": 1_500_000,
        "draw_calls": 1000,
        "texture_vram_mb": 512,
        "max_texture": 4096,
        "materials": 64,
    },
}

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
SEVERITY_WEIGHTS = {"HIGH": 10, "MEDIUM": 5, "LOW": 2}

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

TRIANGLE_MODES = (4,)
STRIP_MODES = (5, 6)
JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


# ---------------------------------------------------------------------------
# Container parsing
# ---------------------------------------------------------------------------


def parse_glb(data: bytes) -> tuple[dict[str, Any], bytes]:
    """Return (gltf_json, bin_chunk_bytes) from a binary glTF container."""
    if len(data) < 12:
        raise ValueError("file too short to be a GLB")
    magic, version, _length = struct.unpack("<III", data[:12])
    if magic != GLB_MAGIC:
        raise ValueError("not a GLB container (bad magic)")
    if version != 2:
        raise ValueError(f"unsupported glTF container version {version}")

    gltf: dict[str, Any] | None = None
    binary = b""
    offset = 12
    while offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack("<II", data[offset : offset + 8])
        offset += 8
        if offset + chunk_len > len(data):
            raise ValueError("truncated GLB chunk")
        chunk = data[offset : offset + chunk_len]
        offset += chunk_len
        if chunk_type == CHUNK_JSON and gltf is None:
            parsed = json.loads(chunk.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("GLB JSON chunk must be an object")
            gltf = parsed
        elif chunk_type == CHUNK_BIN and not binary:
            binary = chunk
    if gltf is None:
        raise ValueError("GLB has no JSON chunk")
    return gltf, binary


def decode_data_uri(uri: str) -> bytes:
    """Decode a RFC 2397 `data:` URI (base64 or percent-encoded)."""
    if not uri.startswith("data:") or "," not in uri:
        return b""
    header, payload = uri[5:].split(",", 1)
    if ";base64" in header.lower():
        try:
            return base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError):
            return b""
    return urllib.parse.unquote_to_bytes(payload)


# ---------------------------------------------------------------------------
# Image dimension probing (stdlib only)
# ---------------------------------------------------------------------------


def png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def _find_jpeg_marker(data: bytes, idx: int, n: int) -> int | None:
    while idx + 1 < n and data[idx] != 0xFF:
        idx += 1
    while idx + 1 < n and data[idx + 1] == 0xFF:
        idx += 1
    return idx if idx + 1 < n else None


def _step_jpeg_segment(
    data: bytes, pos: int, n: int
) -> tuple[tuple[int, int] | None, int | None]:
    marker = data[pos + 1]
    if marker in (0xD9, 0xDA):  # EOI or Start of Scan
        return None, None
    if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
        return None, pos + 2
    if pos + 4 > n:
        return None, None
    seg_len = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
    if seg_len < 2:
        return None, None
    if marker in JPEG_SOF_MARKERS:
        if pos + 9 > n:
            return None, None
        height, width = struct.unpack(">HH", data[pos + 5 : pos + 9])
        return (int(width), int(height)), None
    return None, pos + 2 + seg_len


def jpeg_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i + 1 < n:
        pos = _find_jpeg_marker(data, i, n)
        if pos is None:
            break
        dims, next_i = _step_jpeg_segment(data, pos, n)
        if dims is not None:
            return dims
        if next_i is None:
            break
        i = next_i
    return None


def ktx2_size(data: bytes) -> tuple[int, int] | None:
    """KTX2 identifier is 12 bytes: AB 4B 54 58 20 32 30 BB 0D 0A 1A 0A."""
    if len(data) < 80 or data[:12] != b"\xabKTX 20\xbb\r\n\x1a\n":
        return None
    _vk, _type_size, width, height = struct.unpack("<IIII", data[12:28])
    return int(width), int(height)


def webp_size(data: bytes) -> tuple[int, int] | None:
    """Parse RIFF WebP header (VP8, VP8L, VP8X)."""
    if len(data) < 25 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8L" and data[20] == 0x2F:
        bits = struct.unpack("<I", data[21:25])[0]
        w = (bits & 0x3FFF) + 1
        h = ((bits >> 14) & 0x3FFF) + 1
        return int(w), int(h)
    if len(data) < 30:
        return None
    if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        w, h = struct.unpack("<HH", data[26:30])
        return int(w & 0x3FFF), int(h & 0x3FFF)
    if chunk == b"VP8X":
        w = int.from_bytes(data[24:27], "little") + 1
        h = int.from_bytes(data[27:30], "little") + 1
        return int(w), int(h)
    return None


def probe_image(data: bytes) -> tuple[tuple[int, int] | None, str]:
    """Return ((width, height) or None, format_name)."""
    for probe, name in (
        (png_size, "png"),
        (jpeg_size, "jpeg"),
        (ktx2_size, "ktx2"),
        (webp_size, "webp"),
    ):
        size = probe(data)
        if size:
            return size, name
    return None, "unknown"


# ---------------------------------------------------------------------------
# glTF analysis
# ---------------------------------------------------------------------------


class AssetAuditor:
    def __init__(self, path: str, tier: str = "medium") -> None:
        self.path = path
        self.base_dir = Path(path).resolve().parent
        self.tier = tier
        self.budget = TIERS[tier]
        self.defects: list[dict[str, Any]] = []
        self.stats: dict[str, Any] = {}

    def _add(self, code: str, severity: str, message: str, fix: str) -> None:
        self.defects.append(
            {
                "file": os.path.basename(self.path),
                "line": 0,
                "code": code,
                "severity": severity,
                "message": message,
                "fix": fix,
            }
        )

    def _accessor_count(self, gltf: dict[str, Any], index: int | None) -> int:
        if index is None or index < 0:
            return 0
        accessors = gltf.get("accessors", [])
        if index >= len(accessors):
            return 0
        return int(accessors[index].get("count", 0))

    def _safe_read_uri(self, uri: str) -> bytes:
        if uri.startswith("data:"):
            return decode_data_uri(uri)
        decoded_rel = urllib.parse.unquote(uri)
        if "\x00" in decoded_rel:
            self._add(
                "GLTF_UNSAFE_EXTERNAL_URI",
                "HIGH",
                f"External URI contains null byte: {uri!r}.",
                "Use relative asset paths contained inside the asset directory.",
            )
            return b""
        candidate = (self.base_dir / decoded_rel).resolve()
        if not candidate.is_relative_to(self.base_dir):
            self._add(
                "GLTF_UNSAFE_EXTERNAL_URI",
                "HIGH",
                f"External URI escapes asset directory: {uri!r}.",
                "Keep external buffers and textures inside the asset's base directory.",
            )
            return b""
        if candidate.is_file():
            return candidate.read_bytes()
        return b""

    def _audit_geometry(self, gltf: dict[str, Any]) -> tuple[int, int, int, int, int]:
        meshes = gltf.get("meshes", [])
        triangles = 0
        vertices = 0
        primitives = 0
        untextured_primitives = 0
        no_material_meshes = 0

        for mesh in meshes:
            mesh_prims = mesh.get("primitives", [])
            if not mesh_prims:
                continue
            if not any(
                "material" in p and p["material"] is not None for p in mesh_prims
            ):
                no_material_meshes += 1
            for prim in mesh_prims:
                primitives += 1
                mode = int(prim.get("mode", 4))
                idx = prim.get("indices")
                pos = prim.get("attributes", {}).get("POSITION")
                count = self._accessor_count(gltf, idx)
                if count == 0:
                    count = self._accessor_count(gltf, pos)
                if mode in TRIANGLE_MODES:
                    triangles += count // 3
                elif mode in STRIP_MODES:
                    triangles += max(0, count - 2)
                vertices = max(vertices, self._accessor_count(gltf, pos))
                if prim.get("material") is None:
                    untextured_primitives += 1

        return (
            triangles,
            vertices,
            primitives,
            untextured_primitives,
            no_material_meshes,
        )

    def _read_image_bytes(
        self, image: dict[str, Any], gltf: dict[str, Any], binary: bytes
    ) -> bytes:
        uri = image.get("uri")
        if isinstance(uri, str) and uri:
            return self._safe_read_uri(uri)
        if "bufferView" in image:
            views = gltf.get("bufferViews", [])
            vi = int(image["bufferView"])
            if 0 <= vi < len(views):
                bv = views[vi]
                start = int(bv.get("byteOffset", 0))
                length = int(bv.get("byteLength", 0))
                blob = binary or self._external_buffer(gltf)
                return blob[start : start + length]
        return b""

    def _audit_textures(
        self, gltf: dict[str, Any], binary: bytes
    ) -> tuple[int, int, int, list[dict[str, Any]]]:
        images = gltf.get("images", [])
        vram_bytes = 0
        decoded_bytes = 0
        max_dim = 0
        texture_rows: list[dict[str, Any]] = []

        for image in images:
            data = self._read_image_bytes(image, gltf, binary)
            size, fmt = probe_image(data)
            if size is None:
                texture_rows.append(
                    {
                        "format": str(image.get("mimeType", "?")),
                        "width": None,
                        "height": None,
                    }
                )
                continue
            w, h = size
            max_dim = max(max_dim, w, h)
            decoded = int(w * h * 4 * 1.333)
            decoded_bytes += decoded
            # Include mip chain (~1.333x) on GPU-compressed KTX2 as well as decoded RGBA8
            vram = int(w * h * 1.0 * 1.333) if fmt == "ktx2" else decoded
            vram_bytes += vram
            texture_rows.append(
                {
                    "format": str(image.get("mimeType", fmt)),
                    "width": w,
                    "height": h,
                    "file_bytes": len(data),
                    "vram_bytes": vram,
                }
            )

        return vram_bytes, decoded_bytes, max_dim, texture_rows

    def _check_budgets(
        self,
        triangles: int,
        primitives: int,
        vram_bytes: int,
        max_dim: int,
        material_count: int,
    ) -> None:
        b = self.budget
        if triangles > b["triangles"]:
            self._add(
                "GLTF_TRIANGLE_BUDGET_EXCEEDED",
                "HIGH",
                f"{triangles:,} triangles exceeds the {self.tier} tier ceiling of {b['triangles']:,}.",
                "Decimate the mesh, author LODs, or drop the asset to a lower tier.",
            )
        if primitives > b["draw_calls"]:
            self._add(
                "GLTF_DRAW_CALL_BUDGET_EXCEEDED",
                "HIGH",
                f"{primitives} primitives (≈{primitives} draw calls) exceeds the {self.tier} tier ceiling of {b['draw_calls']}.",
                "Merge primitives that share a material, or use InstancedMesh for repeats.",
            )
        if vram_bytes > b["texture_vram_mb"] * 1024 * 1024:
            self._add(
                "GLTF_TEXTURE_VRAM_EXCEEDED",
                "HIGH",
                f"Texture VRAM ≈{vram_bytes / 1048576:.1f} MB exceeds the {self.tier} tier ceiling of {b['texture_vram_mb']} MB.",
                "Downscale textures, use KTX2/ETC1S, or split the asset set.",
            )
        if max_dim > b["max_texture"]:
            self._add(
                "GLTF_TEXTURE_TOO_LARGE",
                "MEDIUM",
                f"Largest texture is {max_dim}px; the {self.tier} tier caps textures at {b['max_texture']}px.",
                "Downscale the texture set or ship a separate low-tier variant.",
            )
        if material_count > b["materials"]:
            self._add(
                "GLTF_MATERIAL_SLOT_EXPLOSION",
                "MEDIUM",
                f"{material_count} materials exceeds the {self.tier} tier ceiling of {b['materials']}.",
                "Atlas shared materials — each material is a separate draw call and shader variant.",
            )

    def _check_compression_and_lods(
        self, gltf: dict[str, Any], triangles: int, image_count: int
    ) -> tuple[bool, bool, set[str]]:
        used = {str(ext) for ext in gltf.get("extensionsUsed", [])}
        geometry_compressed = bool(
            {"KHR_draco_mesh_compression", "EXT_meshopt_compression"} & used
        )
        texture_compressed = bool({"KHR_texture_basisu", "EXT_texture_webp"} & used)
        if triangles > 0 and not geometry_compressed:
            self._add(
                "GLTF_UNCOMPRESSED_GEOMETRY",
                "MEDIUM",
                "No Draco or meshopt compression — the mesh ships uncompressed (3-10x larger).",
                "Re-export with Draco (static meshes) or meshopt (mobile / streamed scenes).",
            )
        if image_count and not texture_compressed:
            self._add(
                "GLTF_UNCOMPRESSED_TEXTURES",
                "MEDIUM",
                f"{image_count} textures ship as PNG/JPEG — no KTX2 or WebP compression.",
                "Encode to KTX2 (UASTC or ETC1S); the decoded VRAM cost is unchanged but the payload collapses.",
            )
        nodes = gltf.get("nodes", [])
        lod_hint = "MSFT_lod" in used or any(
            "_LOD" in (n.get("name") or "").upper() for n in nodes
        )
        if triangles > 50_000 and not lod_hint:
            self._add(
                "GLTF_MISSING_LOD",
                "MEDIUM",
                f"{triangles:,} triangles with no LOD structure detected. Distant assets cost full price.",
                "Author LODs (100% / 40% / 15%) or ship the MSFT_lod extension.",
            )
        return geometry_compressed, texture_compressed, used

    def _check_nodes_and_materials(
        self,
        gltf: dict[str, Any],
        untextured_primitives: int,
        no_material_meshes: int,
    ) -> None:
        nodes = gltf.get("nodes", [])
        meshes = gltf.get("meshes", [])
        materials = gltf.get("materials", [])

        negative_scale: list[str] = []
        non_uniform_scale: list[str] = []
        for node in nodes:
            scale = node.get("scale")
            if not scale:
                continue
            if any(float(s) < 0 for s in scale):
                negative_scale.append(str(node.get("name", "<unnamed>")))
            elif len({round(float(s), 4) for s in scale}) > 1:
                non_uniform_scale.append(str(node.get("name", "<unnamed>")))

        if negative_scale:
            self._add(
                "GLTF_NEGATIVE_SCALE_NODE",
                "HIGH",
                f"Node(s) with negative scale: {', '.join(negative_scale[:4])}. Negative scale flips normals and tangents — the asset renders inside-out.",
                "Apply the negative scale to the mesh data itself, or bake it into the geometry before export.",
            )
        if non_uniform_scale:
            self._add(
                "GLTF_NON_UNIFORM_SCALE_NODE",
                "LOW",
                f"Node(s) with non-uniform scale: {', '.join(non_uniform_scale[:4])}. Non-uniform scale distorts normal/tangent mapping.",
                "Apply transforms on export, or author the mesh pre-scaled.",
            )

        has_normal_map = any("normalTexture" in m for m in materials)
        has_tangents = any(
            "TANGENT" in p.get("attributes", {})
            for mesh in meshes
            for p in mesh.get("primitives", [])
        )
        if has_normal_map and not has_tangents:
            self._add(
                "GLTF_NORMAL_MAP_WITHOUT_TANGENTS",
                "LOW",
                "Materials use a normal map but no primitive carries TANGENT. three.js falls back to derivative-based tangents, which is lower quality on non-uniform scale.",
                "Export tangents (glTF: 'export tangents' in Blender's glTF addon).",
            )

        if untextured_primitives:
            self._add(
                "GLTF_PRIMITIVE_WITHOUT_MATERIAL",
                "LOW",
                f"{untextured_primitives} primitive(s) have no material — they render with the default material (extra draw call, no PBR response).",
                "Assign a material to every primitive.",
            )
        if no_material_meshes:
            self._add(
                "GLTF_MESH_WITHOUT_MATERIAL",
                "LOW",
                f"{no_material_meshes} mesh(es) have no material assigned.",
                "Assign a material to every mesh.",
            )

    def _check_scale(self, gltf: dict[str, Any]) -> None:
        accessors = gltf.get("accessors", [])
        meshes = gltf.get("meshes", [])
        pos_indices = {
            int(p["attributes"]["POSITION"])
            for mesh in meshes
            for p in mesh.get("primitives", [])
            if isinstance(p.get("attributes", {}).get("POSITION"), int)
        }
        candidate_indices = (
            sorted(pos_indices) if pos_indices else list(range(len(accessors)))
        )
        for idx in candidate_indices:
            if not (0 <= idx < len(accessors)):
                continue
            accessor = accessors[idx]
            if (
                accessor.get("type") == "VEC3"
                and isinstance(accessor.get("min"), list)
                and isinstance(accessor.get("max"), list)
                and len(accessor["min"]) >= 3
                and len(accessor["max"]) >= 3
            ):
                extent = [
                    float(accessor["max"][i]) - float(accessor["min"][i])
                    for i in range(3)
                ]
                largest = max(extent)
                if largest > 0 and (largest < 0.01 or largest > 1000):
                    self._add(
                        "GLTF_SCALE_SUSPICIOUS",
                        "MEDIUM",
                        f"Geometry extent is ~{largest:.4g} units. glTF is defined in METRES — this asset is likely authored in millimetres or kilometres.",
                        "Scale the asset so 1 unit = 1 metre, and scale shadow bias/normalBias to match.",
                    )
                    break

    def audit(self, gltf: dict[str, Any], binary: bytes) -> dict[str, Any]:
        meshes = gltf.get("meshes", [])
        materials = gltf.get("materials", [])
        textures = gltf.get("textures", [])
        images = gltf.get("images", [])
        nodes = gltf.get("nodes", [])

        triangles, vertices, primitives, untextured_primitives, no_material_meshes = (
            self._audit_geometry(gltf)
        )
        vram_bytes, decoded_bytes, max_dim, texture_rows = self._audit_textures(
            gltf, binary
        )
        self._check_budgets(triangles, primitives, vram_bytes, max_dim, len(materials))
        geometry_compressed, texture_compressed, used = (
            self._check_compression_and_lods(gltf, triangles, len(images))
        )
        self._check_nodes_and_materials(gltf, untextured_primitives, no_material_meshes)
        self._check_scale(gltf)

        self.stats = {
            "file": os.path.basename(self.path),
            "tier": self.tier,
            "triangles": triangles,
            "vertices": vertices,
            "draw_calls_estimate": primitives,
            "meshes": len(meshes),
            "nodes": len(nodes),
            "materials": len(materials),
            "textures": len(textures),
            "images": len(images),
            "animations": len(gltf.get("animations", [])),
            "skins": len(gltf.get("skins", [])),
            "cameras": len(gltf.get("cameras", [])),
            "texture_vram_mb": round(vram_bytes / 1048576, 2),
            "texture_decoded_mb": round(decoded_bytes / 1048576, 2),
            "max_texture_dimension": max_dim,
            "geometry_compressed": geometry_compressed,
            "texture_compressed": texture_compressed,
            "extensions_used": sorted(used),
            "textures_detail": texture_rows,
        }
        return self.stats

    def _external_buffer(self, gltf: dict[str, Any]) -> bytes:
        buffers = gltf.get("buffers", [])
        if not buffers:
            return b""
        uri = buffers[0].get("uri")
        if not isinstance(uri, str) or not uri:
            return b""
        return self._safe_read_uri(uri)


def load_asset(path: str) -> tuple[dict[str, Any], bytes]:
    """Load a .gltf (JSON) or .glb (binary container)."""
    with open(path, "rb") as fh:
        data = fh.read()

    if data.lstrip()[:1] == b"{":
        parsed = json.loads(data.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("glTF JSON root must be an object")
        return parsed, b""
    return parse_glb(data)


def _print_human_report(
    stats: dict[str, Any],
    tier: str,
    score: int,
    defects: list[dict[str, Any]],
    out_path: str | None,
) -> None:
    print("\n========================================================")
    print(f" Plastic Surgery glTF Asset Auditor (v{LINTER_VERSION})")
    print(f" Asset: {stats['file']}   Tier: {stats['tier'].upper()}")
    print("========================================================")
    print(
        f" Triangles:      {stats['triangles']:>10,}   (budget {TIERS[tier]['triangles']:,})"
    )
    print(f" Vertices:       {stats['vertices']:>10,}")
    print(
        f" Draw calls ~:   {stats['draw_calls_estimate']:>10,}   (budget {TIERS[tier]['draw_calls']})"
    )
    print(
        f" Materials:      {stats['materials']:>10,}   (budget {TIERS[tier]['materials']})"
    )
    print(f" Textures:       {stats['images']:>10,}")
    print(
        f" Texture VRAM:   {stats['texture_vram_mb']:>9} MB   (budget {TIERS[tier]['texture_vram_mb']} MB)"
    )
    print(
        f" Max texture:    {stats['max_texture_dimension']:>10}px   (budget {TIERS[tier]['max_texture']})"
    )
    print(f" Meshes/Nodes:   {stats['meshes']:>6,} / {stats['nodes']:,}")
    print(f" Animations:     {stats['animations']:>10,}   Skins: {stats['skins']}")
    print(
        f" Geometry compressed: {stats['geometry_compressed']}   Texture compressed: {stats['texture_compressed']}"
    )
    print(f" Extensions:     {', '.join(stats['extensions_used']) or 'none'}")
    print(f" Asset Health Score: {score} / 100")
    print(f" Defects: {len(defects)}")
    print("========================================================\n")

    for d in defects:
        print(f"[{d['severity']}] {d['code']}")
        print(f"  Issue: {d['message']}")
        print(f"  Fix:   {d['fix']}\n")

    if not defects:
        print("✓ Asset is within budget and free of structural defects.\n")

    if out_path:
        print(f"Report saved to: {out_path}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Zero-mutation glTF/GLB asset budget auditor."
    )
    parser.add_argument("asset", help="Path to a .glb or .gltf file")
    parser.add_argument(
        "--tier",
        choices=sorted(TIERS),
        default="medium",
        help="Target device tier (default: medium)",
    )
    parser.add_argument("--out", help="Write JSON audit report to file")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report to stdout",
    )
    parser.add_argument(
        "--fail-on",
        choices=["high", "medium", "low"],
        default=None,
        help="Exit 1 when a defect at or above this severity is present.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.asset):
        print(f"error: no such file: {args.asset}", file=sys.stderr)
        return 2

    try:
        gltf, binary = load_asset(args.asset)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: could not parse {args.asset}: {exc}", file=sys.stderr)
        return 2

    auditor = AssetAuditor(args.asset, args.tier)
    stats = auditor.audit(gltf, binary)

    penalty = sum(SEVERITY_WEIGHTS.get(d["severity"], 2) for d in auditor.defects)
    score = max(0, 100 - penalty)
    defects = sorted(
        auditor.defects, key=lambda d: SEVERITY_ORDER.get(d["severity"], 99)
    )

    report = {
        "asset": stats,
        "budget": TIERS[args.tier],
        "asset_health_score": score,
        "defects_count": len(defects),
        "defects": defects,
    }
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human_report(stats, args.tier, score, defects, args.out)

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on.upper()]
        worst = min((SEVERITY_ORDER[d["severity"]] for d in defects), default=99)
        if worst <= threshold:
            print(
                f"GATE FAILED: defect at or above {args.fail_on.upper()} present.",
                file=sys.stderr if args.json else sys.stdout,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
