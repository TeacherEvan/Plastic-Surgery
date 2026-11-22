#!/usr/bin/env python3
"""
preflight_video_polish.py — Zero-mutation video & surgical-media storyboard auditor.

Audits either:
  1. A `surgical-media` storyboard JSON (`.json`) for palette contrast, active grade,
     linear easings, static/flat scenes, off-canvas or safe-zone breaches, unattributed
     media, and referenced Three.js script / external asset path safety.
  2. A rendered video MP4 (`.mp4` / `.mov` / `.mkv`) via `ffprobe` (and optional `ffmpeg`
     loudness/dead-air measurement) for H.264 + yuv420p, CFR, BT.709 color tags,
     `+faststart` moov placement, AAC 48 kHz audio, and storyboard duration drift.

Stdlib only. Read-only on target inputs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

LINTER_VERSION = "2.0.0"

SEVERITY_WEIGHTS = {"HIGH": 10, "MEDIUM": 5, "LOW": 2}
SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

SARIF_SCHEMA = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
SARIF_LEVELS = {"HIGH": "error", "MEDIUM": "warning", "LOW": "note"}

PRESET_PALETTES: dict[str, dict[str, str]] = {
    "newsroom_clean": {
        "ground": "#0F1720",
        "ink": "#EEF2F6",
        "accent": "#E5484D",
        "accent2": "#5AA9E6",
    },
    "noir_restraint": {
        "ground": "#0B0B0D",
        "ink": "#E8E4DC",
        "accent": "#C8A24A",
        "accent2": "#6B7A8F",
    },
    "punchy_pop": {
        "ground": "#FFF4D6",
        "ink": "#1B1B1F",
        "accent": "#FF4D6D",
        "accent2": "#2EC4B6",
    },
    "risograph": {
        "ground": "#F2EBDD",
        "ink": "#1F2A44",
        "accent": "#FF5A4E",
        "accent2": "#2F6FED",
    },
    "soft_clay": {
        "ground": "#F5E9DD",
        "ink": "#3C3028",
        "accent": "#A65A38",
        "accent2": "#D4E3D6",
    },
    "tech_blueprint": {
        "ground": "#0A1A33",
        "ink": "#DCEBFF",
        "accent": "#4FD1FF",
        "accent2": "#FFB84D",
    },
}

ANIMATED_ELEMENTS = frozenset(
    {
        "orb_pulse",
        "dot_field",
        "orbit_ring",
        "equalizer",
        "typewriter_text",
        "leader_arrow",
        "stick_rig",
        "tesseract",
        "phi_divider",
        "scaling_chart",
        "system_architecture",
        "code_terminal",
        "map_arrow",
        "swipe_card",
        "social_post",
        "chat_bubble",
        "app_toast",
    }
)
SAFE_ZONE_TEXT_ELEMENTS = frozenset(
    {"kinetic_captions", "typewriter_text", "quote_card", "hud_badge", "source_tag"}
)
SAFE_9_16_ORGANIC = (60, 180, 930, 1540)
SAFE_9_16_STRICT = (65, 288, 888, 1248)

_HEX_RE = re.compile(r"^#?([0-9A-Fa-f]{6})(?:[0-9A-Fa-f]{2})?$")
_I_RE = re.compile(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", re.IGNORECASE)
_PEAK_RE = re.compile(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", re.IGNORECASE)
_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9]+(?:\.[0-9]+)?)")
_BLACK_DUR_RE = re.compile(r"black_duration:\s*([0-9]+(?:\.[0-9]+)?)")
_FREEZE_DUR_RE = re.compile(r"freeze_duration:\s*([0-9]+(?:\.[0-9]+)?)")
_YMIN_RE = re.compile(r"lavfi\.signalstats\.YMIN=([0-9]+(?:\.[0-9]+)?)")
_YAVG_RE = re.compile(r"lavfi\.signalstats\.YAVG=([0-9]+(?:\.[0-9]+)?)")
_YMAX_RE = re.compile(r"lavfi\.signalstats\.YMAX=([0-9]+(?:\.[0-9]+)?)")
_SATAVG_RE = re.compile(r"lavfi\.signalstats\.SATAVG=([0-9]+(?:\.[0-9]+)?)")


def classify_format(width: int, height: int) -> str:
    """Classify pixel dimensions into canonical social/video aspect ratios."""
    if width <= 0 or height <= 0:
        return "custom"
    ratio = width / height
    for name, target in (
        ("9:16", 9.0 / 16.0),
        ("16:9", 16.0 / 9.0),
        ("1:1", 1.0),
        ("4:5", 4.0 / 5.0),
    ):
        if abs(ratio - target) <= 0.04:
            return name
    return "custom"


def safe_rect_for(
    fmt: str, safe_mode: str, width: int, height: int
) -> tuple[float, float, float, float]:
    """Return (x0, y0, x1, y1) safe rectangle for the given format and mode."""
    if fmt == "9:16":
        sx, sy = width / 1080.0, height / 1920.0
        x0, y0, x1, y1 = (
            SAFE_9_16_ORGANIC if safe_mode == "organic" else SAFE_9_16_STRICT
        )
        return (x0 * sx, y0 * sy, x1 * sx, y1 * sy)
    if fmt == "16:9":
        inset = 0.05 if safe_mode == "organic" else 0.10
        return (
            width * inset,
            height * inset,
            width * (1.0 - inset),
            height * (1.0 - inset),
        )
    inset = 0.06 if safe_mode == "organic" else 0.10
    return (
        width * inset,
        height * inset,
        width * (1.0 - inset),
        height * (1.0 - inset),
    )


def _srgb_to_linear(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else float(((c + 0.055) / 1.055) ** 2.4)


def wcag_contrast_ratio(hex1: str, hex2: str) -> float:
    """Compute exact WCAG 2.2 relative-luminance contrast ratio for two #RRGGBB colors."""
    m1 = _HEX_RE.match(hex1.strip())
    m2 = _HEX_RE.match(hex2.strip())
    if not m1 or not m2:
        return 0.0

    def lum(h: str) -> float:
        r = _srgb_to_linear(int(h[0:2], 16))
        g = _srgb_to_linear(int(h[2:4], 16))
        b = _srgb_to_linear(int(h[4:6], 16))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    l1, l2 = sorted((lum(m1.group(1)), lum(m2.group(1))), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _read_atom_step(fh: Any, offset: int, size32: int) -> int | None:
    if size32 == 1:
        ext = fh.read(8)
        if len(ext) < 8:
            return None
        step = int(struct.unpack(">Q", ext)[0])
        return step if step >= 16 else None
    if size32 == 0 or size32 < 8:
        return None
    return size32


def check_mp4_faststart(path: Path) -> bool | None:
    """Walk top-level ISO BMFF atoms; True if `moov` precedes `mdat`."""
    try:
        file_size = path.stat().st_size
        with path.open("rb") as fh:
            offset = 0
            for _ in range(1024):
                if offset + 8 > file_size:
                    break
                fh.seek(offset)
                hdr = fh.read(8)
                if len(hdr) < 8:
                    break
                size32, atom = struct.unpack(">I4s", hdr)
                if atom == b"moov":
                    return True
                if atom == b"mdat":
                    return False
                step = _read_atom_step(fh, offset, size32)
                if step is None:
                    break
                offset += step
    except OSError:
        return None
    return None


def _defect(
    file: str, line: int, code: str, severity: str, message: str, fix: str
) -> dict[str, Any]:
    return {
        "file": file,
        "line": line,
        "code": code,
        "severity": severity,
        "message": message,
        "fix": fix,
    }


def _resolve_board_palette_and_grade(
    board: dict[str, Any], name: str, defects: list[dict[str, Any]]
) -> dict[str, Any]:
    style = board.get("style")
    preset = str(style.get("preset", "")) if isinstance(style, dict) else ""
    palette = dict(PRESET_PALETTES.get(preset, {}))
    if isinstance(style, dict) and isinstance(style.get("palette"), dict):
        for k, v in style["palette"].items():
            if isinstance(v, str):
                palette[str(k)] = v

    grade = style.get("grade") if isinstance(style, dict) else None
    has_active_grade = preset in PRESET_PALETTES or (
        isinstance(grade, dict)
        and any(
            float(grade.get(k, 0) or 0) != 0
            for k in ("grain", "vignette", "halation", "warmth")
        )
    )
    if not isinstance(style, dict) or not has_active_grade:
        defects.append(
            _defect(
                name,
                0,
                "STORYBOARD_MISSING_STYLE_BIBLE",
                "MEDIUM",
                "Storyboard has no style preset or active finishing grade (grain/vignette/halation/warmth).",
                "Add a verified style.preset or style.palette + style.grade block (see tactile_tokens_and_surfaces.md §6).",
            )
        )

    ink_cr: float | None = None
    acc_cr: float | None = None
    ground = palette.get("ground", "")
    ink = palette.get("ink", "")
    accent = palette.get("accent", "")
    if ground and ink:
        ink_cr = round(wcag_contrast_ratio(ink, ground), 2)
        if ink_cr < 4.5:
            defects.append(
                _defect(
                    name,
                    0,
                    "STORYBOARD_LOW_CONTRAST_PALETTE",
                    "HIGH",
                    f"Palette ink ({ink}) vs ground ({ground}) contrast is {ink_cr}:1 (< 4.5:1 WCAG AA).",
                    "Darken/lighten ink or ground to achieve >= 4.5:1 contrast.",
                )
            )
    if ground and accent:
        acc_cr = round(wcag_contrast_ratio(accent, ground), 2)
        if acc_cr < 3.0:
            defects.append(
                _defect(
                    name,
                    0,
                    "STORYBOARD_LOW_CONTRAST_PALETTE",
                    "MEDIUM",
                    f"Palette accent ({accent}) vs ground ({ground}) contrast is {acc_cr}:1 (< 3.0:1 UI minimum).",
                    "Adjust accent lightness or use a verified palette from tactile_tokens_and_surfaces.md §6.",
                )
            )
    return {
        "style_preset": preset or None,
        "ink_ground_contrast": ink_cr,
        "accent_ground_contrast": acc_cr,
        "has_grade": has_active_grade,
    }


def _scene_has_motion(scene: dict[str, Any]) -> bool:
    cam = scene.get("camera")
    if isinstance(cam, dict):
        mode = str(cam.get("mode", "zoom"))
        if mode == "orbit":
            return True
        if float(cam.get("shake_amplitude_px", 0) or 0) > 0:
            return True
        if mode == "zoom" and (
            float(cam.get("zoom_start", 1.0) or 1.0)
            != float(cam.get("zoom_end", 1.0) or 1.0)
            or cam.get("pan_x") is not None
            or cam.get("pan_y") is not None
        ):
            return True
    for el in scene.get("elements") or []:
        if not isinstance(el, dict):
            continue
        etype = str(el.get("type", ""))
        if etype in ANIMATED_ELEMENTS or (etype == "svg" and el.get("reveal")):
            return True
        if etype == "image" and (
            float(el.get("kb_zoom", 1.0) or 1.0) > 1.001
            or float(el.get("fade_in_sec", 0) or 0) > 0
        ):
            return True
    return False


def _check_scene_motion_and_cuts(
    board: dict[str, Any],
    scenes: list[dict[str, Any]],
    name: str,
    defects: list[dict[str, Any]],
) -> None:
    style = board.get("style")
    motion = style.get("motion") if isinstance(style, dict) else None
    if isinstance(motion, dict) and motion.get("ease") == "linear":
        defects.append(
            _defect(
                name,
                0,
                "STORYBOARD_LINEAR_EASING",
                "HIGH",
                "style.motion.ease uses 'linear', which violates non-linear motion invariants.",
                "Use ease_out_expo, ease_in_out_cubic, ease_in_out_sine, or spring_pop.",
            )
        )

    eases: list[str] = []
    hard_cut_run = 0
    for idx, scene in enumerate(scenes):
        sid = str(scene.get("scene_id", f"scene_{idx}"))
        cam = scene.get("camera")
        if isinstance(cam, dict):
            for key in ("easing", "orbit_easing"):
                val = cam.get(key)
                if val == "linear":
                    defects.append(
                        _defect(
                            name,
                            0,
                            "STORYBOARD_LINEAR_EASING",
                            "HIGH",
                            f"Scene '{sid}' camera.{key} uses 'linear'.",
                            "Replace 'linear' with ease_out_expo, ease_in_out_cubic, or spring_pop.",
                        )
                    )
                elif isinstance(val, str) and val:
                    eases.append(val)

        dur = float(scene.get("duration_sec", 0) or 0)
        if (
            "scene_spec" not in scene
            and not scene.get("silent_beat")
            and dur >= 2.0
            and not _scene_has_motion(scene)
        ):
            defects.append(
                _defect(
                    name,
                    0,
                    "STORYBOARD_FLAT_STATIC_SCENE",
                    "LOW",
                    f"2D scene '{sid}' ({dur:.1f}s) has no camera move or animated element.",
                    "Add a subtle camera zoom/orbit or an animated element (orb_pulse, dot_field, svg reveal).",
                )
            )

        has_transition = (
            float(scene.get("fade_in_sec", 0) or 0) > 0
            or float(scene.get("fade_out_sec", 0) or 0) > 0
            or scene.get("transition") == "dissolve"
        )
        hard_cut_run = 0 if has_transition else hard_cut_run + 1
        if hard_cut_run == 4:
            defects.append(
                _defect(
                    name,
                    0,
                    "STORYBOARD_HARD_CUT_MONOTONY",
                    "LOW",
                    f"4+ consecutive scenes ending at '{sid}' have zero fades or dissolve transitions.",
                    "Add subtle fade_in_sec/fade_out_sec (0.15-0.3s) or transition: 'dissolve' at section shifts.",
                )
            )

    if len(eases) >= 4 and len(set(eases)) == 1:
        defects.append(
            _defect(
                name,
                0,
                "STORYBOARD_SINGLE_EASING",
                "LOW",
                f"All {len(eases)} camera moves use '{eases[0]}'.",
                "Vary easings across beats (e.g. ease_out_expo for hooks, ease_in_out_cubic for body).",
            )
        )


def _pair_coords(raw: Any) -> list[tuple[float, float]]:
    if not isinstance(raw, list):
        return []
    return [
        (float(p[0]), float(p[1])) for p in raw if isinstance(p, list) and len(p) >= 2
    ]


def _element_coords(el: dict[str, Any]) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    box = el.get("box")
    if isinstance(box, list) and len(box) == 4:
        pts.extend([(float(box[0]), float(box[1])), (float(box[2]), float(box[3]))])
    for kx, ky in (("x", "y"), ("cx", "cy")):
        if el.get(kx) is not None and el.get(ky) is not None:
            pts.append((float(el[kx]), float(el[ky])))
    pts.extend(_pair_coords(el.get("points")))
    for n in el.get("nodes") or []:
        if isinstance(n, dict) and n.get("x") is not None and n.get("y") is not None:
            pts.append((float(n["x"]), float(n["y"])))
    reach_to = el.get("reach_to")
    if isinstance(reach_to, list) and len(reach_to) >= 2:
        pts.append((float(reach_to[0]), float(reach_to[1])))
    if el.get("bar_top") is not None:
        pts.append((0.0, float(el["bar_top"])))
    return pts


def _check_scene_elements_and_safe_zones(
    scenes: list[dict[str, Any]],
    width: int,
    height: int,
    safe_rect: tuple[float, float, float, float],
    name: str,
    defects: list[dict[str, Any]],
) -> None:
    sx0, sy0, sx1, sy1 = safe_rect
    for idx, scene in enumerate(scenes):
        sid = str(scene.get("scene_id", f"scene_{idx}"))
        for el in scene.get("elements") or []:
            if not isinstance(el, dict):
                continue
            etype = str(el.get("type", ""))
            if etype == "image" and not str(el.get("attribution", "")).strip():
                defects.append(
                    _defect(
                        name,
                        0,
                        "STORYBOARD_UNATTRIBUTED_MEDIA",
                        "HIGH",
                        f"Scene '{sid}' image element lacks an 'attribution' string.",
                        "Add 'attribution' from assets/manifest.json or CREDITS.md.",
                    )
                )
            pts = _element_coords(el)
            off = any(x < 0 or x > width or y < 0 or y > height for x, y in pts)
            if off:
                defects.append(
                    _defect(
                        name,
                        0,
                        "STORYBOARD_OFF_CANVAS_ELEMENT",
                        "HIGH",
                        f"Scene '{sid}' element '{etype}' has coordinates outside {width}x{height}.",
                        "Clamp element coordinates inside the canvas dimensions.",
                    )
                )
            elif etype in SAFE_ZONE_TEXT_ELEMENTS and pts:
                breach = any(x < sx0 or x > sx1 or y < sy0 or y > sy1 for x, y in pts)
                if breach:
                    defects.append(
                        _defect(
                            name,
                            0,
                            "STORYBOARD_SAFE_ZONE_BREACH",
                            "MEDIUM",
                            f"Scene '{sid}' '{etype}' falls outside safe box ({sx0:.0f},{sy0:.0f})..({sx1:.0f},{sy1:.0f}).",
                            "Move text/HUD coordinates inside the platform safe rectangle.",
                        )
                    )
            if etype == "image" and el.get("attribution_y") is not None:
                ay = float(el["attribution_y"])
                if ay < sy0 or ay > sy1:
                    defects.append(
                        _defect(
                            name,
                            0,
                            "STORYBOARD_SAFE_ZONE_BREACH",
                            "MEDIUM",
                            f"Scene '{sid}' image.attribution_y={ay:.0f} falls outside safe vertical band [{sy0:.0f}, {sy1:.0f}].",
                            "Set attribution_y inside the platform safe zone.",
                        )
                    )


def _resolve_color_ref(raw: Any, palette: dict[str, str]) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    val = raw.strip()
    if val.startswith("@"):
        return palette.get(val[1:])
    return val if _HEX_RE.match(val) else None


def _check_element_contrast(
    scenes: list[dict[str, Any]],
    palette: dict[str, str],
    name: str,
    defects: list[dict[str, Any]],
) -> None:
    text_types = {"typewriter_text", "quote_card", "source_tag", "map_callout"}
    for idx, scene in enumerate(scenes):
        sid = str(scene.get("scene_id", f"scene_{idx}"))
        els = [e for e in scene.get("elements") or [] if isinstance(e, dict)]
        scene_bg = palette.get("ground")
        for el in els:
            if el.get("type") == "background":
                bg_c = _resolve_color_ref(el.get("color"), palette)
                if bg_c:
                    scene_bg = bg_c
        for el in els:
            if str(el.get("type", "")) not in text_types:
                continue
            fg = (
                _resolve_color_ref(el.get("color"), palette)
                or _resolve_color_ref(el.get("ink_color"), palette)
                or _resolve_color_ref(el.get("text_color"), palette)
            )
            bg = (
                _resolve_color_ref(el.get("fill"), palette)
                or _resolve_color_ref(el.get("bg"), palette)
                or scene_bg
            )
            if fg and bg:
                cr = round(wcag_contrast_ratio(fg, bg), 2)
                if cr < 4.5:
                    defects.append(
                        _defect(
                            name,
                            0,
                            "STORYBOARD_ELEMENT_LOW_CONTRAST",
                            "MEDIUM",
                            f"Scene '{sid}' element '{el.get('type')}' contrast {fg} on {bg} is {cr}:1 (< 4.5:1).",
                            "Adjust element foreground/fill color to meet >= 4.5:1 WCAG AA contrast.",
                        )
                    )


def _audit_3d_param_path(
    base_dir: Path,
    sid: str,
    key: str,
    raw: str,
    name: str,
    defects: list[dict[str, Any]],
) -> None:
    candidate = (base_dir / raw).resolve()
    if not candidate.is_relative_to(base_dir):
        defects.append(
            _defect(
                name,
                0,
                "STORYBOARD_UNSAFE_ASSET_PATH",
                "HIGH",
                f"Scene '{sid}' {key} '{raw}' escapes storyboard directory.",
                "Keep referenced 3D scripts and assets inside the storyboard directory.",
            )
        )
    elif key == "threejs_script" and candidate.is_file():
        from preflight_visual_lint import VisualAuditor

        res = VisualAuditor(str(candidate)).scan()
        for d in res["defects"]:
            if d["severity"] in ("HIGH", "MEDIUM"):
                defects.append(
                    _defect(
                        name,
                        int(d["line"]),
                        "STORYBOARD_THREEJS_SCRIPT_DEFECT",
                        "MEDIUM",
                        f"Referenced Three.js script '{raw}' [{d['code']}]: {d['message']}",
                        str(d["fix"]),
                    )
                )
    elif (
        key == "asset_path"
        and candidate.is_file()
        and raw.lower().endswith((".glb", ".gltf"))
    ):
        from preflight_gltf_budget import AssetAuditor, load_asset

        try:
            gltf, binary = load_asset(str(candidate))
            aud = AssetAuditor(str(candidate), "medium")
            aud.audit(gltf, binary)
            for d in aud.defects:
                if d["severity"] in ("HIGH", "MEDIUM"):
                    defects.append(
                        _defect(
                            name,
                            0,
                            "STORYBOARD_GLTF_BUDGET_DEFECT",
                            str(d["severity"]),
                            f"Referenced 3D asset '{raw}' [{d['code']}]: {d['message']}",
                            str(d["fix"]),
                        )
                    )
        except (ValueError, json.JSONDecodeError, OSError):
            pass


def _check_scene_3d_references(
    board_path: Path,
    scenes: list[dict[str, Any]],
    name: str,
    defects: list[dict[str, Any]],
) -> tuple[int, int]:
    base_dir = board_path.resolve().parent
    threejs_scenes = 0
    external_glb = 0
    for idx, scene in enumerate(scenes):
        sid = str(scene.get("scene_id", f"scene_{idx}"))
        if str(scene.get("backend", "")).startswith("threejs"):
            threejs_scenes += 1
        spec = scene.get("scene_spec")
        params = spec.get("params") if isinstance(spec, dict) else None
        if not isinstance(params, dict):
            continue
        for key in ("threejs_script", "asset_path"):
            raw = params.get(key)
            if not isinstance(raw, str) or not raw.strip():
                continue
            if key == "asset_path" and raw.lower().endswith((".glb", ".gltf")):
                external_glb += 1
            _audit_3d_param_path(base_dir, sid, key, raw, name, defects)
    return threejs_scenes, external_glb


def audit_storyboard(
    board_path: Path, safe_mode: str, forced_format: str
) -> dict[str, Any]:
    """Audit a surgical-media storyboard JSON file without mutating it."""
    board = cast(dict[str, Any], json.loads(board_path.read_text(encoding="utf-8")))
    name = board_path.name
    defects: list[dict[str, Any]] = []

    raw_fmt = board.get("format")
    fmt_obj: dict[str, Any] = raw_fmt if isinstance(raw_fmt, dict) else {}
    width = int(fmt_obj.get("width", 1280) or 1280)
    height = int(fmt_obj.get("height", 720) or 720)
    fps = float(fmt_obj.get("fps", 30) or 30)
    fmt = classify_format(width, height) if forced_format == "auto" else forced_format
    safe_rect = safe_rect_for(fmt, safe_mode, width, height)

    scenes = [s for s in board.get("scenes", []) if isinstance(s, dict)]
    total_dur = round(sum(float(s.get("duration_sec", 0) or 0) for s in scenes), 3)

    style_metrics = _resolve_board_palette_and_grade(board, name, defects)
    style = board.get("style")
    preset = str(style.get("preset", "")) if isinstance(style, dict) else ""
    resolved_pal = dict(PRESET_PALETTES.get(preset, {}))
    if isinstance(style, dict) and isinstance(style.get("palette"), dict):
        for k, v in style["palette"].items():
            if isinstance(v, str):
                resolved_pal[str(k)] = v
    _check_scene_motion_and_cuts(board, scenes, name, defects)
    _check_scene_elements_and_safe_zones(
        scenes, width, height, safe_rect, name, defects
    )
    _check_element_contrast(scenes, resolved_pal, name, defects)
    threejs_scenes, external_glb = _check_scene_3d_references(
        board_path, scenes, name, defects
    )

    metrics: dict[str, Any] = {
        "width": width,
        "height": height,
        "fps": fps,
        "scenes_count": len(scenes),
        "total_duration_sec": total_dur,
        **style_metrics,
        "threejs_scenes": threejs_scenes,
        "external_glb_assets": external_glb,
    }
    return _finalize_report(
        str(board_path), "storyboard", fmt, safe_mode, metrics, defects
    )


def _parse_rate(rate: Any) -> float | None:
    num, _, den = str(rate or "0/1").partition("/")
    try:
        d = float(den or 1)
        return float(num) / d if d > 0 else None
    except ValueError:
        return None


def _run_ffprobe(video_path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return cast(dict[str, Any], json.loads(proc.stdout))


def _measure_audio_loudness_and_silence(
    video_path: Path, name: str, defects: list[dict[str, Any]]
) -> tuple[float | None, float | None, int | None]:
    if shutil.which("ffmpeg") is None:
        return None, None, None
    lufs: float | None = None
    peak: float | None = None
    dead_air: int | None = None

    ebur = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video_path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    i_matches = [float(m) for m in _I_RE.findall(ebur.stderr)]
    p_matches = [float(m) for m in _PEAK_RE.findall(ebur.stderr)]
    if i_matches:
        lufs = round(i_matches[-1], 2)
    if p_matches:
        peak = round(p_matches[-1], 2)
    if (lufs is not None and abs(lufs - (-14.0)) > 1.0) or (
        peak is not None and peak > -1.0
    ):
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_LOUDNESS_OUT_OF_RANGE",
                "MEDIUM",
                f"Audio loudness I={lufs} LUFS, Peak={peak} dBFS (target -14.0 +/- 1.0 LUFS, <= -1.0 dBTP).",
                "Apply two-pass ffmpeg loudnorm=I=-14:TP=-1.5:LRA=11:linear=true.",
            )
        )

    sil = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video_path),
            "-af",
            "silencedetect=noise=-50dB:d=0.6",
            "-f",
            "null",
            "-",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    starts = [float(m) for m in _SILENCE_START_RE.findall(sil.stderr)]
    ends = [float(m) for m in _SILENCE_END_RE.findall(sil.stderr)]
    long_gaps = [(e - s) for s, e in zip(starts, ends, strict=False) if (e - s) > 0.61]
    dead_air = len(long_gaps)
    if dead_air > 0:
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_DEAD_AIR_DETECTED",
                "LOW",
                f"Detected {dead_air} dead-air interval(s) > 0.6s.",
                "Tighten beat pacing or add ambient pad/SFX under silent gaps.",
            )
        )
    return lufs, peak, dead_air


def _measure_visual_telemetry(
    video_path: Path, name: str, defects: list[dict[str, Any]]
) -> tuple[int | None, int | None, float | None, float | None, float | None]:
    if shutil.which("ffmpeg") is None:
        return None, None, None, None, None
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(video_path),
            "-vf",
            "blackdetect=d=0.4:pix_th=0.10,freezedetect=n=-60dB:d=2.5,fps=1,signalstats,metadata=mode=print:file=-",
            "-f",
            "null",
            "-",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    black_count = len(_BLACK_DUR_RE.findall(proc.stderr))
    freeze_count = len(_FREEZE_DUR_RE.findall(proc.stderr))
    if black_count > 0:
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_BLACK_FRAMES_DETECTED",
                "MEDIUM",
                f"Detected {black_count} black-frame interval(s) >= 0.4s.",
                "Trim dead black frames or add intro/outro fade content.",
            )
        )
    if freeze_count > 0:
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_FROZEN_FRAMES_DETECTED",
                "LOW",
                f"Detected {freeze_count} frozen-frame interval(s) >= 2.5s.",
                "Add subtle camera zoom/orbit or animated motion layer.",
            )
        )

    yavgs = [float(m) for m in _YAVG_RE.findall(proc.stdout)]
    ymins = [float(m) for m in _YMIN_RE.findall(proc.stdout)]
    ymaxs = [float(m) for m in _YMAX_RE.findall(proc.stdout)]
    sats = [float(m) for m in _SATAVG_RE.findall(proc.stdout)]
    avg_luma = round(sum(yavgs) / len(yavgs), 2) if yavgs else None
    luma_range = (
        round(
            sum(hi - lo for hi, lo in zip(ymaxs, ymins, strict=False)) / len(ymins), 2
        )
        if ymins and ymaxs
        else None
    )
    avg_sat = round(sum(sats) / len(sats), 2) if sats else None
    if luma_range is not None and luma_range < 40.0 and black_count == 0:
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_LOW_DYNAMIC_RANGE",
                "LOW",
                f"Sampled frame luma range is {luma_range} (< 40.0); image may look flat/washed.",
                "Apply subtle contrast curve (eq=contrast=1.05 or curves) in single-pass grade.",
            )
        )
    return black_count, freeze_count, avg_luma, luma_range, avg_sat


def _check_video_streams(
    video: dict[str, Any] | None,
    audio: dict[str, Any] | None,
    video_path: Path,
    name: str,
    defects: list[dict[str, Any]],
) -> dict[str, Any]:
    if video is None or audio is None:
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_MISSING_STREAM",
                "HIGH",
                "MP4 must contain both a video stream and an audio stream.",
                "Mux H.264 video with 48 kHz stereo AAC audio.",
            )
        )

    width = int(video.get("width", 0)) if video else 0
    height = int(video.get("height", 0)) if video else 0
    r_fps = _parse_rate(video.get("r_frame_rate")) if video else None
    avg_fps = _parse_rate(video.get("avg_frame_rate")) if video else None
    v_codec = (
        str(video.get("codec_name")) if video and video.get("codec_name") else None
    )
    pix_fmt = str(video.get("pix_fmt")) if video and video.get("pix_fmt") else None
    c_space = (
        str(video.get("color_space")) if video and video.get("color_space") else None
    )
    c_prim = (
        str(video.get("color_primaries"))
        if video and video.get("color_primaries")
        else None
    )
    c_trc = (
        str(video.get("color_transfer"))
        if video and video.get("color_transfer")
        else None
    )

    if video and v_codec != "h264":
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_UNSUPPORTED_CODEC",
                "HIGH",
                f"Video codec is '{v_codec}'; H.264 ('h264') is required for universal social playback.",
                "Re-encode with -c:v libx264 -profile:v high -level 4.2.",
            )
        )
    if video and pix_fmt != "yuv420p":
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_INVALID_PIX_FMT",
                "HIGH",
                f"Pixel format is '{pix_fmt}'; 'yuv420p' is required for iOS/Safari/IG/TikTok.",
                "Add format=yuv420p to the filter graph or -pix_fmt yuv420p.",
            )
        )
    if r_fps and avg_fps and abs(r_fps - avg_fps) > max(0.05, 0.005 * r_fps):
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_VFR_DETECTED",
                "HIGH",
                f"Variable frame rate detected (r_frame_rate={r_fps:.3f}, avg_frame_rate={avg_fps:.3f}).",
                "Normalize to constant frame rate with -vf fps=30 (or 60).",
            )
        )
    if video and (c_space != "bt709" or c_prim != "bt709" or c_trc != "bt709"):
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_MISSING_BT709_TAGS",
                "MEDIUM",
                f"Missing explicit BT.709 tags (space={c_space}, primaries={c_prim}, transfer={c_trc}).",
                "Pass -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv.",
            )
        )

    faststart = check_mp4_faststart(video_path)
    if faststart is False:
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_MISSING_FASTSTART",
                "MEDIUM",
                "MP4 'mdat' atom precedes 'moov' atom (missing +faststart).",
                "Re-mux or encode with -movflags +faststart for instant web/social streaming.",
            )
        )

    a_codec = (
        str(audio.get("codec_name")) if audio and audio.get("codec_name") else None
    )
    a_sr = (
        int(audio.get("sample_rate", 0) or 0)
        if audio and audio.get("sample_rate")
        else None
    )
    a_ch = (
        int(audio.get("channels", 0) or 0) if audio and audio.get("channels") else None
    )
    if audio and (a_codec != "aac" or a_sr != 48000):
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_AUDIO_FORMAT_MISMATCH",
                "MEDIUM",
                f"Audio stream is {a_codec} @ {a_sr} Hz; AAC @ 48000 Hz is required.",
                "Encode audio with -c:a aac -b:a 192k -ar 48000 -ac 2.",
            )
        )

    v_prof = str(video.get("profile")) if video and video.get("profile") else None
    raw_lvl = video.get("level") if video else None
    v_lvl = int(raw_lvl) if raw_lvl is not None else None
    sar = (
        str(video.get("sample_aspect_ratio"))
        if video and video.get("sample_aspect_ratio")
        else None
    )
    if sar and sar not in ("1:1", "0:1", "N/A"):
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_NON_SQUARE_PIXELS",
                "MEDIUM",
                f"Non-square sample_aspect_ratio '{sar}' detected (expected 1:1).",
                "Add setsar=1 to the ffmpeg filter chain.",
            )
        )
    if (
        video
        and v_codec == "h264"
        and (
            (
                v_prof
                and v_prof not in ("High", "Main", "Constrained Baseline", "Baseline")
            )
            or (v_lvl is not None and max(width, height) <= 1920 and v_lvl > 42)
        )
    ):
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_H264_PROFILE_OR_LEVEL",
                "MEDIUM",
                f"H.264 profile={v_prof}, level={v_lvl} exceeds High@4.2 compatibility.",
                "Encode with -profile:v high -level 4.2.",
            )
        )

    return {
        "width": width,
        "height": height,
        "fps": round(r_fps, 3) if r_fps else None,
        "avg_fps": round(avg_fps, 3) if avg_fps else None,
        "video_codec": v_codec,
        "video_profile": v_prof,
        "video_level": v_lvl,
        "sample_aspect_ratio": sar,
        "pix_fmt": pix_fmt,
        "color_space": c_space,
        "color_primaries": c_prim,
        "color_transfer": c_trc,
        "audio_codec": a_codec,
        "audio_sample_rate": a_sr,
        "audio_channels": a_ch,
        "faststart": faststart,
    }


def audit_video(
    video_path: Path,
    storyboard_path: Path | None,
    safe_mode: str,
    forced_format: str,
    measure_audio: bool,
    measure_visual: bool = False,
) -> dict[str, Any]:
    """Audit a rendered MP4 against social/surgical-media delivery invariants."""
    probe = _run_ffprobe(video_path)
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    name = video_path.name
    defects: list[dict[str, Any]] = []

    metrics = _check_video_streams(video, audio, video_path, name, defects)
    fmt_info = probe.get("format") or {}
    raw_dur = fmt_info.get("duration")
    duration = float(raw_dur) if raw_dur is not None else None
    metrics["duration_sec"] = round(duration, 3) if duration is not None else None
    raw_br = fmt_info.get("bit_rate")
    bitrate_kbps = round(float(raw_br) / 1000.0, 1) if raw_br is not None else None
    metrics["bitrate_kbps"] = bitrate_kbps
    raw_sz = fmt_info.get("size")
    size_bytes = int(raw_sz) if raw_sz is not None else video_path.stat().st_size
    metrics["file_size_mb"] = round(size_bytes / 1_000_000.0, 2)
    if (
        max(int(metrics["width"] or 0), int(metrics["height"] or 0)) >= 1080
        and bitrate_kbps is not None
        and bitrate_kbps < 1500.0
    ):
        defects.append(
            _defect(
                name,
                0,
                "VIDEO_BITRATE_ANOMALY",
                "LOW",
                f"1080p+ video bitrate is {bitrate_kbps:.0f} kbps (< 1500 kbps); detail may look blocky.",
                "Encode with -crf 18 -preset slow for clean 1080p social mastering.",
            )
        )

    drift_ms: float | None = None
    if storyboard_path is not None:
        board = cast(
            dict[str, Any], json.loads(storyboard_path.read_text(encoding="utf-8"))
        )
        bfmt = board.get("format") or {}
        bw, bh = int(bfmt.get("width", 0) or 0), int(bfmt.get("height", 0) or 0)
        bfps = float(bfmt.get("fps", 0) or 0)
        if (
            (bw and metrics["width"] != bw)
            or (bh and metrics["height"] != bh)
            or (bfps and metrics["fps"] and abs(metrics["fps"] - bfps) > 0.05)
        ):
            defects.append(
                _defect(
                    name,
                    0,
                    "VIDEO_DIMENSION_MISMATCH",
                    "HIGH",
                    f"Video {metrics['width']}x{metrics['height']}@{metrics['fps']}fps != storyboard {bw}x{bh}@{bfps}fps.",
                    "Re-render or scale/fps-normalize to match storyboard format.",
                )
            )
        expected_dur = sum(
            float(s.get("duration_sec", 0) or 0) for s in board.get("scenes", [])
        )
        if duration is not None and expected_dur > 0:
            drift_ms = round(abs(duration - expected_dur) * 1000.0, 1)
            if drift_ms > 150.0:
                defects.append(
                    _defect(
                        name,
                        0,
                        "VIDEO_DURATION_DRIFT",
                        "HIGH",
                        f"A/V duration drift {drift_ms:.0f} ms exceeds 150 ms ceiling.",
                        "Re-run tts_align.py or trim/pad audio in a single-pass encode.",
                    )
                )
    metrics["storyboard_drift_ms"] = drift_ms

    lufs, peak, dead_air = (
        _measure_audio_loudness_and_silence(video_path, name, defects)
        if measure_audio
        else (None, None, None)
    )
    metrics["integrated_lufs"] = lufs
    metrics["true_peak_dbtp"] = peak
    metrics["dead_air_count"] = dead_air

    black_c, freeze_c, avg_luma, luma_range, avg_sat = (
        _measure_visual_telemetry(video_path, name, defects)
        if measure_visual
        else (None, None, None, None, None)
    )
    metrics["black_intervals"] = black_c
    metrics["freeze_intervals"] = freeze_c
    metrics["avg_luma"] = avg_luma
    metrics["luma_range"] = luma_range
    metrics["avg_saturation"] = avg_sat

    fmt = (
        classify_format(int(metrics["width"] or 0), int(metrics["height"] or 0))
        if forced_format == "auto"
        else forced_format
    )
    return _finalize_report(str(video_path), "video", fmt, safe_mode, metrics, defects)


def _finalize_report(
    target: str,
    mode: str,
    fmt: str,
    safe_mode: str,
    metrics: dict[str, Any],
    defects: list[dict[str, Any]],
) -> dict[str, Any]:
    penalty = sum(SEVERITY_WEIGHTS.get(d["severity"], 2) for d in defects)
    score = max(0, 100 - penalty)
    sorted_defects = sorted(
        defects, key=lambda d: SEVERITY_ORDER.get(d["severity"], 99)
    )
    return {
        "target": target,
        "mode": mode,
        "format": fmt,
        "safe_mode": safe_mode,
        "metrics": metrics,
        "video_health_score": score,
        "defects_count": len(sorted_defects),
        "defects": sorted_defects,
    }


def build_sarif(results: dict[str, Any]) -> dict[str, Any]:
    """Convert video polish audit results into a valid SARIF 2.1.0 payload."""
    seen_rules: dict[str, dict[str, Any]] = {}
    sarif_results: list[dict[str, Any]] = []
    for defect in results["defects"]:
        code = str(defect["code"])
        if code not in seen_rules:
            seen_rules[code] = {
                "id": code,
                "shortDescription": {"text": code.replace("_", " ").title()},
                "help": {"text": str(defect["fix"])},
            }
        sarif_results.append(
            {
                "ruleId": code,
                "level": SARIF_LEVELS.get(str(defect["severity"]), "note"),
                "message": {"text": f"{defect['message']} Fix: {defect['fix']}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": str(defect["file"]).replace(os.sep, "/")
                            },
                            "region": {"startLine": max(1, int(defect["line"]))},
                        }
                    }
                ],
            }
        )
    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "plastic-surgery-preflight-video-polish",
                        "version": LINTER_VERSION,
                        "informationUri": "https://github.com/TeacherEvan/Plastic-Surgery",
                        "rules": list(seen_rules.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }


def _print_human_report(results: dict[str, Any], out_path: str | None) -> None:
    print("\n========================================================")
    print(f" Plastic Surgery Video Polish Auditor (v{LINTER_VERSION})")
    print(
        f" Target: {results['target']}  [{results['mode'].upper()} | {results['format']} | {results['safe_mode']}]"
    )
    print(f" Video Health Score: {results['video_health_score']} / 100")
    print(f" Detected Defects:   {results['defects_count']}")
    print("========================================================\n")
    for d in results["defects"][:20]:
        print(f"[{d['severity']}] {d['code']} at {d['file']}:{d['line']}")
        print(f"  Issue: {d['message']}")
        print(f"  Fix:   {d['fix']}\n")
    if not results["defects"]:
        print("✓ Zero video polish or storyboard defects detected.")
    if out_path:
        print(f"\nReport saved to: {out_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Zero-mutation video MP4 and surgical-media storyboard auditor."
    )
    parser.add_argument("target", help="Path to a storyboard .json or rendered .mp4")
    parser.add_argument(
        "--storyboard", help="Optional storyboard .json for MP4 drift/dimension checks"
    )
    parser.add_argument(
        "--format",
        choices=["auto", "9:16", "16:9", "1:1", "4:5"],
        default="auto",
        help="Target aspect format (default: auto-detect)",
    )
    parser.add_argument(
        "--safe-mode",
        choices=["organic", "strict"],
        default="strict",
        help="Safe-zone mask preset (default: strict)",
    )
    parser.add_argument(
        "--measure-audio",
        action="store_true",
        help="Run ffmpeg ebur128 loudness and silencedetect checks on MP4s",
    )
    parser.add_argument(
        "--measure-visual",
        action="store_true",
        help="Run ffmpeg blackdetect, freezedetect, and signalstats telemetry on MP4s",
    )
    parser.add_argument("--out", help="Write JSON or SARIF report to file")
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON report to stdout"
    )
    parser.add_argument(
        "--sarif", action="store_true", help="Emit SARIF 2.1.0 report to stdout"
    )
    parser.add_argument(
        "--fail-on",
        choices=["high", "medium", "low"],
        default=None,
        help="Exit 1 when a defect at or above this severity is present.",
    )
    args = parser.parse_args(argv)

    target_path = Path(args.target)
    if not target_path.is_file():
        print(f"error: no such file: {args.target}", file=sys.stderr)
        return 2

    storyboard_path = Path(args.storyboard) if args.storyboard else None
    if storyboard_path is not None and not storyboard_path.is_file():
        print(f"error: no such storyboard: {args.storyboard}", file=sys.stderr)
        return 2

    try:
        if target_path.suffix.lower() == ".json":
            results = audit_storyboard(target_path, args.safe_mode, args.format)
        else:
            if shutil.which("ffprobe") is None:
                print("error: ffprobe not found on PATH", file=sys.stderr)
                return 2
            results = audit_video(
                target_path,
                storyboard_path,
                args.safe_mode,
                args.format,
                args.measure_audio,
                args.measure_visual,
            )
    except (
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
        OSError,
    ) as exc:
        print(f"error: failed to audit {args.target}: {exc}", file=sys.stderr)
        return 2

    payload: dict[str, Any] = build_sarif(results) if args.sarif else results
    if args.out:
        out_p = Path(args.out).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.sarif or args.json:
        print(json.dumps(payload, indent=2))
    else:
        _print_human_report(results, args.out)

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on.upper()]
        worst = min(
            (SEVERITY_ORDER[d["severity"]] for d in results["defects"]), default=99
        )
        if worst <= threshold:
            print(
                f"GATE FAILED: defect at or above {args.fail_on.upper()} present.",
                file=sys.stderr if (args.sarif or args.json) else sys.stdout,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
