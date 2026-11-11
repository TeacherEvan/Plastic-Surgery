#!/usr/bin/env python3
"""
preflight_gltf_budget.py — Zero-mutation glTF 2.0 / GLB asset budget auditor.

Inspects an authored 3D asset against the Plastic Surgery render budgets:
triangle counts, draw calls, texture VRAM, material slots, texture dimensions,
LOD coverage and compression coverage — then reports what the asset will cost
at runtime.

Usage:
    python3 scripts/preflight_gltf_budget.py asset.glb [--tier medium] [--out report.json]

Supports:
    * .glb  — binary glTF (JSON chunk + BIN chunk)
    * .gltf — JSON glTF with external resources (images measured from the
              referenced files when they are present on disk)

Stdlib only. All operations are strictly read-only.

Tier budgets (see references/threejs_3d_asset_pipeline.md §2, Stage 1):

    tier      triangles   draw calls   texture VRAM   max texture   materials
    low           60 k          80          64 MB        1024          16
    medium       300 k         250         256 MB        2048          32
    high        1.5 M        1000         512 MB        4096          64
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from typing import Any, Dict, List, Optional, Tuple

LINTER_VERSION = "1.3.0"

TIERS: Dict[str, Dict[str, int]] = {
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


# ---------------------------------------------------------------------------
# Container parsing
# ---------------------------------------------------------------------------

def parse_glb(data: bytes) -> Tuple[Dict[str, Any], bytes]:
    """Return (gltf_json, bin_chunk_bytes) from a binary glTF container."""
    if len(data) < 12:
        raise ValueError("file too short to be a GLB")
    magic, version, _length = struct.unpack("<III", data[:12])
    if magic != GLB_MAGIC:
        raise ValueError("not a GLB container (bad magic)")
    if version != 2:
        raise ValueError(f"unsupported glTF container version {version}")

    gltf: Optional[Dict[str, Any]] = None
    binary = b""
    offset = 12
    while offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack("<II", data[offset:offset + 8])
        offset += 8
        chunk = data[offset:offset + chunk_len]
        offset += chunk_len
        if chunk_type == CHUNK_JSON and gltf is None:
            gltf = json.loads(chunk.decode("utf-8"))
        elif chunk_type == CHUNK_BIN and not binary:
            binary = chunk
    if gltf is None:
        raise ValueError("GLB has no JSON chunk")
    return gltf, binary


# ---------------------------------------------------------------------------
# Image dimension probing (stdlib only)
# ---------------------------------------------------------------------------

def png_size(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def jpeg_size(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        # SOF0..SOF3, SOF5..SOF7, SOF9..SOF11, SOF13..SOF15
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return int(width), int(height)
        i += 2 + seg_len
    return None


def ktx2_size(data: bytes) -> Optional[Tuple[int, int]]:
    """KTX2 identifier is 12 bytes: AB 4B 54 58 20 32 30 BB 0D 0A 1A 0A."""
    if len(data) < 80 or data[:12] != b"\xabKTX 20\xbb\r\n\x1a\n":
        return None
    _vk, _type_size, width, height = struct.unpack("<IIII", data[12:28])
    return int(width), int(height)


def probe_image(data: bytes) -> Tuple[Optional[Tuple[int, int]], str]:
    """Return ((width, height) or None, format_name)."""
    for probe, name in ((png_size, "png"), (jpeg_size, "jpeg"), (ktx2_size, "ktx2")):
        size = probe(data)
        if size:
            return size, name
    return None, "unknown"


# ---------------------------------------------------------------------------
# glTF analysis
# ---------------------------------------------------------------------------

class AssetAuditor:
    def __init__(self, path: str, tier: str = "medium"):
        self.path = path
        self.tier = tier
        self.budget = TIERS[tier]
        self.defects: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}

    # -- helpers ---------------------------------------------------------
    def _add(self, code: str, severity: str, message: str, fix: str) -> None:
        self.defects.append({
            "file": os.path.basename(self.path),
            "line": 0,
            "code": code,
            "severity": severity,
            "message": message,
            "fix": fix,
        })

    def _accessor_count(self, gltf: Dict[str, Any], index: Optional[int]) -> int:
        if index is None:
            return 0
        accessors = gltf.get("accessors", [])
        if index >= len(accessors):
            return 0
        return int(accessors[index].get("count", 0))

    # -- main ------------------------------------------------------------
    def audit(self, gltf: Dict[str, Any], binary: bytes) -> Dict[str, Any]:
        meshes = gltf.get("meshes", [])
        materials = gltf.get("materials", [])
        textures = gltf.get("textures", [])
        images = gltf.get("images", [])
        nodes = gltf.get("nodes", [])
        accessors = gltf.get("accessors", [])

        # --- geometry ---
        triangles = 0
        vertices = 0
        primitives = 0
        untextured_primitives = 0
        no_material_meshes = 0
        for mesh in meshes:
            mesh_prims = mesh.get("primitives", [])
            if not mesh_prims:
                continue
            if not mesh.get("material") and not any("material" in p for p in mesh_prims):
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
                if "material" not in prim:
                    untextured_primitives += 1

        # --- textures ---
        vram_bytes = 0
        decoded_bytes = 0
        max_dim = 0
        texture_rows: List[Dict[str, Any]] = []
        for image in images:
            data = b""
            uri = image.get("uri")
            if uri and not uri.startswith("data:"):
                candidate = os.path.join(os.path.dirname(os.path.abspath(self.path)), uri)
                if os.path.isfile(candidate):
                    with open(candidate, "rb") as fh:
                        data = fh.read()
            elif "bufferView" in image:
                view = gltf.get("bufferViews", [])
                vi = image["bufferView"]
                if vi < len(view):
                    bv = view[vi]
                    start = int(bv.get("byteOffset", 0))
                    length = int(bv.get("byteLength", 0))
                    blob = binary or self._external_buffer(gltf)
                    data = blob[start:start + length]
            size, fmt = probe_image(data)
            if size is None:
                texture_rows.append({"format": image.get("mimeType", "?"), "width": None, "height": None})
                continue
            w, h = size
            max_dim = max(max_dim, w, h)
            file_bytes = len(data)
            # Decoded RGBA8 footprint with a full mip chain (~1.333x).
            decoded = int(w * h * 4 * 1.333)
            decoded_bytes += decoded
            # On-GPU footprint for GPU-compressed formats is far smaller.
            if fmt == "ktx2":
                vram = int(w * h * 1.0)  # conservative BC7/UASTC-ish estimate
            else:
                vram = decoded
            vram_bytes += vram
            texture_rows.append({
                "format": image.get("mimeType", fmt),
                "width": w,
                "height": h,
                "file_bytes": file_bytes,
                "vram_bytes": vram,
            })

        # --- budget checks ---
        b = self.budget
        if triangles > b["triangles"]:
            self._add(
                "GLTF_TRIANGLE_BUDGET_EXCEEDED", "HIGH",
                f"{triangles:,} triangles exceeds the {self.tier} tier ceiling of {b['triangles']:,}.",
                "Decimate the mesh, author LODs, or drop the asset to a lower tier.",
            )
        if primitives > b["draw_calls"]:
            self._add(
                "GLTF_DRAW_CALL_BUDGET_EXCEEDED", "HIGH",
                f"{primitives} primitives (≈{primitives} draw calls) exceeds the {self.tier} tier ceiling of {b['draw_calls']}.",
                "Merge primitives that share a material, or use InstancedMesh for repeats.",
            )
        if vram_bytes > b["texture_vram_mb"] * 1024 * 1024:
            self._add(
                "GLTF_TEXTURE_VRAM_EXCEEDED", "HIGH",
                f"Texture VRAM ≈{vram_bytes / 1048576:.1f} MB exceeds the {self.tier} tier ceiling of {b['texture_vram_mb']} MB.",
                "Downscale textures, use KTX2/ETC1S, or split the asset set.",
            )
        if max_dim > b["max_texture"]:
            self._add(
                "GLTF_TEXTURE_TOO_LARGE", "MEDIUM",
                f"Largest texture is {max_dim}px; the {self.tier} tier caps textures at {b['max_texture']}px.",
                "Downscale the texture set or ship a separate low-tier variant.",
            )
        if len(materials) > b["materials"]:
            self._add(
                "GLTF_MATERIAL_SLOT_EXPLOSION", "MEDIUM",
                f"{len(materials)} materials exceeds the {self.tier} tier ceiling of {b['materials']}.",
                "Atlas shared materials — each material is a separate draw call and shader variant.",
            )

        # --- compression coverage ---
        used = set(gltf.get("extensionsUsed", []))
        geometry_compressed = bool(
            {"KHR_draco_mesh_compression", "EXT_meshopt_compression"} & used
        )
        texture_compressed = bool(
            {"KHR_texture_basisu", "EXT_texture_webp"} & used
        )
        if triangles > 0 and not geometry_compressed:
            self._add(
                "GLTF_UNCOMPRESSED_GEOMETRY", "MEDIUM",
                "No Draco or meshopt compression — the mesh ships uncompressed (3-10x larger).",
                "Re-export with Draco (static meshes) or meshopt (mobile / streamed scenes).",
            )
        if images and not texture_compressed:
            self._add(
                "GLTF_UNCOMPRESSED_TEXTURES", "MEDIUM",
                f"{len(images)} textures ship as PNG/JPEG — no KTX2 or WebP compression.",
                "Encode to KTX2 (UASTC or ETC1S); the decoded VRAM cost is unchanged but the payload collapses.",
            )

        # --- node transforms ---
        negative_scale = []
        non_uniform_scale = []
        for node in nodes:
            scale = node.get("scale")
            if not scale:
                continue
            if any(float(s) < 0 for s in scale):
                negative_scale.append(node.get("name", "<unnamed>"))
            elif len({round(float(s), 4) for s in scale}) > 1:
                non_uniform_scale.append(node.get("name", "<unnamed>"))
        if negative_scale:
            self._add(
                "GLTF_NEGATIVE_SCALE_NODE", "HIGH",
                f"Node(s) with negative scale: {', '.join(negative_scale[:4])}. Negative scale flips normals and tangents — the asset renders inside-out.",
                "Apply the negative scale to the mesh data itself, or bake it into the geometry before export.",
            )
        if non_uniform_scale:
            self._add(
                "GLTF_NON_UNIFORM_SCALE_NODE", "LOW",
                f"Node(s) with non-uniform scale: {', '.join(non_uniform_scale[:4])}. Non-uniform scale distorts normal/tangent mapping.",
                "Apply transforms on export, or author the mesh pre-scaled.",
            )

        # --- normal maps / tangents ---
        has_normal_map = any(
            "normalTexture" in m for m in materials
        )
        has_tangents = any(
            "TANGENT" in p.get("attributes", {}) for mesh in meshes for p in mesh.get("primitives", [])
        )
        if has_normal_map and not has_tangents:
            self._add(
                "GLTF_NORMAL_MAP_WITHOUT_TANGENTS", "LOW",
                "Materials use a normal map but no primitive carries TANGENT. three.js falls back to derivative-based tangents, which is lower quality on non-uniform scale.",
                "Export tangents (glTF: 'export tangents' in Blender's glTF addon).",
            )

        # --- LOD coverage ---
        has_lod = "MSFT_lod" in used
        lod_hint = has_lod or any(
            "_LOD" in (n.get("name") or "").upper() for n in nodes
        )
        if triangles > 50_000 and not lod_hint:
            self._add(
                "GLTF_MISSING_LOD", "MEDIUM",
                f"{triangles:,} triangles with no LOD structure detected. Distant assets cost full price.",
                "Author LODs (100% / 40% / 15%) or ship the MSFT_lod extension.",
            )

        # --- material hygiene ---
        if untextured_primitives:
            self._add(
                "GLTF_PRIMITIVE_WITHOUT_MATERIAL", "LOW",
                f"{untextured_primitives} primitive(s) have no material — they render with the default material (extra draw call, no PBR response).",
                "Assign a material to every primitive.",
            )
        if no_material_meshes:
            self._add(
                "GLTF_MESH_WITHOUT_MATERIAL", "LOW",
                f"{no_material_meshes} mesh(es) have no material assigned.",
                "Assign a material to every mesh.",
            )

        # --- scale sanity ---
        for accessor in accessors:
            if accessor.get("type") == "VEC3" and "min" in accessor and "max" in accessor:
                extent = [
                    float(accessor["max"][i]) - float(accessor["min"][i]) for i in range(3)
                ]
                largest = max(extent)
                if largest > 0 and (largest < 0.01 or largest > 1000):
                    self._add(
                        "GLTF_SCALE_SUSPICIOUS", "MEDIUM",
                        f"Geometry extent is ~{largest:.4g} units. glTF is defined in METRES — this asset is likely authored in millimetres or kilometres.",
                        "Scale the asset so 1 unit = 1 metre, and scale shadow bias/normalBias to match.",
                    )
                break

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

    def _external_buffer(self, gltf: Dict[str, Any]) -> bytes:
        buffers = gltf.get("buffers", [])
        if not buffers:
            return b""
        uri = buffers[0].get("uri")
        if not uri or uri.startswith("data:"):
            return b""
        candidate = os.path.join(os.path.dirname(os.path.abspath(self.path)), uri)
        if os.path.isfile(candidate):
            with open(candidate, "rb") as fh:
                return fh.read()
        return b""


def load_asset(path: str) -> Tuple[Dict[str, Any], bytes]:
    """Load a .gltf (JSON) or .glb (binary container).

    NB: the GLB magic number 0x46546C67 is literally the ASCII bytes "glTF",
    so a naive `startswith(b"glTF")` check misreads every binary GLB as JSON.
    Detect the format by whether the payload is a JSON object.
    """
    with open(path, "rb") as fh:
        data = fh.read()

    if data.lstrip()[:1] == b"{":
        return json.loads(data.decode("utf-8")), b""
    return parse_glb(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero-mutation glTF/GLB asset budget auditor.")
    parser.add_argument("asset", help="Path to a .glb or .gltf file")
    parser.add_argument("--tier", choices=sorted(TIERS), default="medium",
                        help="Target device tier (default: medium)")
    parser.add_argument("--out", help="Write JSON audit report to file")
    parser.add_argument("--fail-on", choices=["high", "medium", "low"], default=None,
                        help="Exit 1 when a defect at or above this severity is present.")
    args = parser.parse_args()

    if not os.path.isfile(args.asset):
        print(f"error: no such file: {args.asset}")
        return 2

    try:
        gltf, binary = load_asset(args.asset)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: could not parse {args.asset}: {exc}")
        return 2

    auditor = AssetAuditor(args.asset, args.tier)
    stats = auditor.audit(gltf, binary)

    penalty = sum(SEVERITY_WEIGHTS.get(d["severity"], 2) for d in auditor.defects)
    score = max(0, 100 - penalty)
    defects = sorted(auditor.defects, key=lambda d: SEVERITY_ORDER.get(d["severity"], 99))

    print(f"\n========================================================")
    print(f" Plastic Surgery glTF Asset Auditor (v{LINTER_VERSION})")
    print(f" Asset: {stats['file']}   Tier: {stats['tier'].upper()}")
    print(f"========================================================")
    print(f" Triangles:      {stats['triangles']:>10,}   (budget {TIERS[args.tier]['triangles']:,})")
    print(f" Vertices:       {stats['vertices']:>10,}")
    print(f" Draw calls ~:   {stats['draw_calls_estimate']:>10,}   (budget {TIERS[args.tier]['draw_calls']})")
    print(f" Materials:      {stats['materials']:>10,}   (budget {TIERS[args.tier]['materials']})")
    print(f" Textures:       {stats['images']:>10,}")
    print(f" Texture VRAM:   {stats['texture_vram_mb']:>9} MB   (budget {TIERS[args.tier]['texture_vram_mb']} MB)")
    print(f" Max texture:    {stats['max_texture_dimension']:>10}px   (budget {TIERS[args.tier]['max_texture']})")
    print(f" Meshes/Nodes:   {stats['meshes']:>6,} / {stats['nodes']:,}")
    print(f" Animations:     {stats['animations']:>10,}   Skins: {stats['skins']}")
    print(f" Geometry compressed: {stats['geometry_compressed']}   Texture compressed: {stats['texture_compressed']}")
    print(f" Extensions:     {', '.join(stats['extensions_used']) or 'none'}")
    print(f" Asset Health Score: {score} / 100")
    print(f" Defects: {len(defects)}")
    print(f"========================================================\n")

    for d in defects:
        print(f"[{d['severity']}] {d['code']}")
        print(f"  Issue: {d['message']}")
        print(f"  Fix:   {d['fix']}\n")

    if not defects:
        print("✓ Asset is within budget and free of structural defects.\n")

    report = {
        "asset": stats,
        "budget": TIERS[args.tier],
        "asset_health_score": score,
        "defects_count": len(defects),
        "defects": defects,
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report saved to: {args.out}\n")

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on.upper()]
        worst = min((SEVERITY_ORDER[d["severity"]] for d in defects), default=99)
        if worst <= threshold:
            print(f"GATE FAILED: defect at or above {args.fail_on.upper()} present.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
