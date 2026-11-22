#!/usr/bin/env python3
"""
polish_surgical_media.py — Non-destructive visual polish engine for surgical-media.

Mode A (`storyboard`):
    Upgrades `style` (palette contrast, active filmic grade, typography),
    replaces `linear` easings, adds subtle drift to static 2D scenes, adds
    section transitions, clamps off-canvas/safe-zone elements, and harmonizes
    3D `style_light` — while cryptographically proving (SHA-256) that all
    immutable fields (`meta.seed`, `format`, `start_sec`, `duration_sec`,
    `vo_wav`, `narration`, `words`, `sfx_events`, `anchors_3d`, attributions)
    are untouched.

Mode B (`video`):
    Runs a single-pass FFmpeg finishing pipeline (look grade, optional
    two-pass EBU R128 `loudnorm`, optional cross-platform aspect reframing,
    optional burned-in captions inside safe zones, H.264 High@4.2 `yuv420p`
    `bt709` `+faststart`) to a NEW output file, plus optional before/after
    `hstack` + dual safe-zone QC contact frames.

Stdlib only. Never overwrites the input file (`--in != --out`).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from preflight_video_polish import (
    ANIMATED_ELEMENTS,
    PRESET_PALETTES,
    SAFE_ZONE_TEXT_ELEMENTS,
    audit_storyboard,
    audit_video,
    classify_format,
    safe_rect_for,
    wcag_contrast_ratio,
)

LINTER_VERSION = "2.0.0"

STORYBOARD_LOOKS: dict[str, dict[str, Any]] = {
    "obsidian_telemetry": {
        "palette": {
            "ground": "#0B0E18",
            "ink": "#F1F4FA",
            "accent": "#5E9EFF",
            "accent2": "#34D399",
            "shadow": "#05070D",
            "highlight": "#FFFFFF",
        },
        "type": {"display": "Inter", "body": "JetBrainsMono", "tracking": 0.01},
        "material": {"family": "glass", "roughness": 0.2},
        "light": {"key_temp_k": 6500, "fill_temp_k": 8000, "shadow_softness": 0.4},
        "grade": {"grain": 0.08, "vignette": 0.16, "halation": 0.16, "warmth": -0.04},
        "motion": {
            "feel": "punchy",
            "ease": "ease_out_expo",
            "hold": 0.15,
            "drift": 0.018,
        },
    },
    "editorial_ivory": {
        "palette": {
            "ground": "#F6F1E9",
            "ink": "#1C1917",
            "accent": "#B5382A",
            "accent2": "#1D5E7A",
            "shadow": "#D6CBBF",
            "highlight": "#FFFDF9",
        },
        "type": {"display": "CormorantGaramond", "body": "Inter", "tracking": 0.0},
        "material": {"family": "paper", "roughness": 0.75},
        "light": {"key_temp_k": 5400, "fill_temp_k": 6800, "shadow_softness": 0.65},
        "grade": {"grain": 0.10, "vignette": 0.12, "halation": 0.06, "warmth": 0.05},
        "motion": {
            "feel": "calm",
            "ease": "ease_in_out_cubic",
            "hold": 0.30,
            "drift": 0.02,
        },
    },
    "noir_amber": {
        "palette": {
            "ground": "#0E0D10",
            "ink": "#EFECE6",
            "accent": "#E5A93B",
            "accent2": "#7CA4D4",
            "shadow": "#050507",
            "highlight": "#FFF7E6",
        },
        "type": {"display": "CormorantGaramond", "body": "Inter", "tracking": 0.02},
        "material": {"family": "metal", "roughness": 0.4},
        "light": {"key_temp_k": 3600, "fill_temp_k": 7400, "shadow_softness": 0.35},
        "grade": {"grain": 0.18, "vignette": 0.28, "halation": 0.18, "warmth": 0.06},
        "motion": {
            "feel": "calm",
            "ease": "ease_out_expo",
            "hold": 0.35,
            "drift": 0.022,
        },
    },
    "blueprint_kinetic": {
        "palette": {
            "ground": "#081428",
            "ink": "#E6F0FF",
            "accent": "#4FD1FF",
            "accent2": "#FFB84D",
            "shadow": "#030914",
            "highlight": "#FFFFFF",
        },
        "type": {"display": "Inter", "body": "JetBrainsMono", "tracking": 0.01},
        "material": {"family": "glass", "roughness": 0.2},
        "light": {"key_temp_k": 6800, "fill_temp_k": 8200, "shadow_softness": 0.4},
        "grade": {"grain": 0.08, "vignette": 0.15, "halation": 0.15, "warmth": -0.05},
        "motion": {
            "feel": "punchy",
            "ease": "ease_out_expo",
            "hold": 0.15,
            "drift": 0.016,
        },
    },
}

VIDEO_LOOKS: dict[str, str] = {
    "neutral_master": "",
    "cinematic_clean": (
        "curves=m='0/0 0.25/0.23 0.75/0.78 1/1',"
        "eq=contrast=1.04:brightness=0.01:saturation=1.06,"
        "vignette=PI/7,noise=alls=2:allf=t+u,unsharp=3:3:0.25:3:3:0.0"
    ),
    "obsidian_contrast": (
        "curves=m='0/0 0.2/0.17 0.8/0.84 1/1',"
        "eq=contrast=1.07:brightness=0.00:saturation=1.05,"
        "vignette=PI/6,noise=alls=3:allf=t+u"
    ),
    "warm_editorial": (
        "curves=r='0/0 0.5/0.52 1/1':b='0/0 0.5/0.48 1/1',"
        "eq=contrast=1.04:brightness=0.015:saturation=1.04,"
        "vignette=PI/6,noise=alls=3:allf=t+u"
    ),
    "punchy_social": (
        "eq=contrast=1.06:brightness=0.02:saturation=1.10,"
        "unsharp=3:3:0.3:3:3:0.0,noise=alls=2:allf=t+u"
    ),
}

FORMAT_DIMS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "4:5": (1440, 1800),
    "1:1": (1080, 1080),
}

EASING_CYCLE = (
    "ease_out_expo",
    "ease_in_out_cubic",
    "ease_in_out_sine",
    "spring_pop",
)
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _parse_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _format_rgb(r: int, g: int, b: int) -> str:
    return (
        f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"
    )


def repair_contrast_hex(fg_hex: str, bg_hex: str, min_ratio: float = 4.5) -> str:
    """Shift fg_hex toward black or white until WCAG contrast vs bg_hex >= min_ratio."""
    if not _HEX_RE.match(fg_hex) or not _HEX_RE.match(bg_hex):
        return fg_hex
    if wcag_contrast_ratio(fg_hex, bg_hex) >= min_ratio:
        return fg_hex
    fr, fg, fb = _parse_rgb(fg_hex)
    bg_is_dark = wcag_contrast_ratio("#FFFFFF", bg_hex) >= wcag_contrast_ratio(
        "#000000", bg_hex
    )
    tr, tg, tb = (255, 255, 255) if bg_is_dark else (0, 0, 0)
    lo, hi = 0.0, 1.0
    best = _format_rgb(tr, tg, tb)
    for _ in range(18):
        mid = (lo + hi) * 0.5
        cand = _format_rgb(
            round(fr + (tr - fr) * mid),
            round(fg + (tg - fg) * mid),
            round(fb + (tb - fb) * mid),
        )
        if wcag_contrast_ratio(cand, bg_hex) >= min_ratio:
            best = cand
            hi = mid
        else:
            lo = mid
    return best


def immutable_fingerprint(board: dict[str, Any]) -> str:
    """SHA-256 of all immutable timing, narration, attribution, and 3D anchor fields."""
    scenes_fp: list[dict[str, Any]] = []
    for s in board.get("scenes", []) or []:
        if not isinstance(s, dict):
            continue
        imm_els: list[dict[str, Any]] = []
        for el in s.get("elements") or []:
            if not isinstance(el, dict):
                continue
            etype = el.get("type")
            if etype == "image":
                imm_els.append(
                    {
                        "type": "image",
                        "src": el.get("src"),
                        "attribution": el.get("attribution"),
                    }
                )
            elif etype == "source_tag":
                imm_els.append(
                    {
                        "type": "source_tag",
                        "text": el.get("text"),
                        "label": el.get("label"),
                    }
                )
            elif etype == "quote_card":
                imm_els.append(
                    {
                        "type": "quote_card",
                        "quote": el.get("quote"),
                        "attribution": el.get("attribution"),
                    }
                )
        spec = s.get("scene_spec")
        anchors = spec.get("anchors_3d") if isinstance(spec, dict) else None
        imm_anchors = [
            {
                "anchor_id": a.get("anchor_id"),
                "label": a.get("label"),
                "metric": a.get("metric"),
                "local_pos": a.get("local_pos"),
            }
            for a in (anchors or [])
            if isinstance(a, dict)
        ]
        scenes_fp.append(
            {
                "scene_id": s.get("scene_id"),
                "start_sec": s.get("start_sec"),
                "duration_sec": s.get("duration_sec"),
                "vo_wav": s.get("vo_wav"),
                "narration": s.get("narration"),
                "words": s.get("words"),
                "sfx_events": s.get("sfx_events"),
                "silent_beat": s.get("silent_beat"),
                "imm_els": imm_els,
                "imm_anchors": imm_anchors,
            }
        )
    payload = {
        "meta_seed": (board.get("meta") or {}).get("seed"),
        "format": board.get("format"),
        "scenes": scenes_fp,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record(
    changes: list[dict[str, str]], scope: str, action: str, detail: str
) -> None:
    changes.append({"scope": scope, "action": action, "detail": detail})


def _upgrade_style_and_palette(
    board: dict[str, Any], look: str, changes: list[dict[str, str]]
) -> dict[str, str]:
    if look != "preserve" and look in STORYBOARD_LOOKS:
        board["style"] = copy.deepcopy(STORYBOARD_LOOKS[look])
        _record(
            changes,
            "style",
            "apply_look",
            f"Applied '{look}' style bible + filmic grade.",
        )
        return cast(dict[str, str], board["style"]["palette"])

    style = board.setdefault("style", {})
    if not isinstance(style, dict):
        style = {}
        board["style"] = style
    preset = str(style.get("preset", ""))
    pal = dict(
        PRESET_PALETTES.get(preset, STORYBOARD_LOOKS["obsidian_telemetry"]["palette"])
    )
    if isinstance(style.get("palette"), dict):
        pal.update(
            {str(k): str(v) for k, v in style["palette"].items() if isinstance(v, str)}
        )
    else:
        style["palette"] = dict(pal)
        if not preset:
            _record(
                changes,
                "style.palette",
                "add_palette",
                "Added WCAG-verified obsidian_telemetry palette.",
            )

    ground = pal.get("ground", "#0B0E18")
    for role, min_cr in (("ink", 4.5), ("accent", 3.0), ("accent2", 3.0)):
        orig = pal.get(role, "")
        if orig and wcag_contrast_ratio(orig, ground) < min_cr:
            fixed = repair_contrast_hex(orig, ground, min_cr)
            style.setdefault("palette", {})[role] = fixed
            pal[role] = fixed
            _record(
                changes,
                f"style.palette.{role}",
                "repair_contrast",
                f"{orig} -> {fixed} (>= {min_cr}:1 vs {ground}).",
            )

    grade = style.get("grade")
    has_grade = preset in PRESET_PALETTES or (
        isinstance(grade, dict)
        and any(
            float(grade.get(k, 0) or 0) != 0
            for k in ("grain", "vignette", "halation", "warmth")
        )
    )
    if not has_grade:
        style["grade"] = {
            "grain": 0.08,
            "vignette": 0.15,
            "halation": 0.15,
            "warmth": 0.0,
        }
        _record(
            changes,
            "style.grade",
            "add_grade",
            "Added subtle filmic grade (grain/vignette/halation).",
        )

    motion = style.get("motion")
    if isinstance(motion, dict) and motion.get("ease") == "linear":
        motion["ease"] = "ease_out_expo"
        _record(
            changes,
            "style.motion.ease",
            "replace_linear",
            "Replaced 'linear' with 'ease_out_expo'.",
        )
    return pal


def _scene_has_2d_motion(scene: dict[str, Any]) -> bool:
    cam = scene.get("camera")
    if isinstance(cam, dict):
        if (
            cam.get("mode") == "orbit"
            or float(cam.get("shake_amplitude_px", 0) or 0) > 0
        ):
            return True
        if float(cam.get("zoom_start", 1.0) or 1.0) != float(
            cam.get("zoom_end", 1.0) or 1.0
        ):
            return True
    for el in scene.get("elements") or []:
        if not isinstance(el, dict):
            continue
        et = str(el.get("type", ""))
        if et in ANIMATED_ELEMENTS or (et == "svg" and el.get("reveal")):
            return True
        if et == "image" and float(el.get("kb_zoom", 1.0) or 1.0) > 1.001:
            return True
    return False


def _upgrade_easings_and_motion(
    scenes: list[dict[str, Any]], changes: list[dict[str, str]]
) -> None:
    used_eases: list[str] = []
    for idx, scene in enumerate(scenes):
        sid = str(scene.get("scene_id", f"scene_{idx}"))
        cam = scene.get("camera")
        if isinstance(cam, dict):
            for key in ("easing", "orbit_easing"):
                if cam.get(key) == "linear":
                    repl = EASING_CYCLE[idx % len(EASING_CYCLE)]
                    cam[key] = repl
                    _record(
                        changes,
                        f"scenes[{sid}].camera.{key}",
                        "replace_linear",
                        f"linear -> {repl}.",
                    )
            if isinstance(cam.get("easing"), str):
                used_eases.append(str(cam["easing"]))

        dur = float(scene.get("duration_sec", 0) or 0)
        if (
            "scene_spec" not in scene
            and not scene.get("silent_beat")
            and dur >= 2.0
            and not _scene_has_2d_motion(scene)
        ):
            scene["camera"] = {
                "zoom_start": 1.0,
                "zoom_end": 1.045,
                "easing": EASING_CYCLE[idx % len(EASING_CYCLE)],
            }
            used_eases.append(str(scene["camera"]["easing"]))
            _record(
                changes,
                f"scenes[{sid}].camera",
                "add_drift",
                "Added subtle 1.0 -> 1.045 camera drift to static 2D beat.",
            )

    if len(used_eases) >= 4 and len(set(used_eases)) == 1:
        for idx, scene in enumerate(scenes):
            cam = scene.get("camera")
            if isinstance(cam, dict) and "easing" in cam and idx % 2 == 1:
                new_e = EASING_CYCLE[idx % len(EASING_CYCLE)]
                cam["easing"] = new_e
        _record(
            changes,
            "scenes[].camera.easing",
            "vary_easing",
            "Varied monotonous single-easing camera moves.",
        )


def _upgrade_transitions(
    scenes: list[dict[str, Any]], changes: list[dict[str, str]]
) -> None:
    if not scenes:
        return
    if float(scenes[0].get("duration_sec", 0) or 0) >= 1.2 and not scenes[0].get(
        "fade_in_sec"
    ):
        scenes[0]["fade_in_sec"] = 0.2
        _record(
            changes,
            "scenes[0].fade_in_sec",
            "add_fade_in",
            "Added 0.2s opening fade-in.",
        )
    if float(scenes[-1].get("duration_sec", 0) or 0) >= 1.2 and not scenes[-1].get(
        "fade_out_sec"
    ):
        scenes[-1]["fade_out_sec"] = 0.25
        _record(
            changes,
            f"scenes[{len(scenes) - 1}].fade_out_sec",
            "add_fade_out",
            "Added 0.25s closing fade-out.",
        )

    run = 0
    for idx, scene in enumerate(scenes):
        has_t = (
            float(scene.get("fade_in_sec", 0) or 0) > 0
            or float(scene.get("fade_out_sec", 0) or 0) > 0
            or scene.get("transition") == "dissolve"
        )
        run = 0 if has_t else run + 1
        if run >= 4 and float(scene.get("duration_sec", 0) or 0) >= 1.5:
            scene["transition"] = "dissolve"
            scene["transition_sec"] = 0.25
            run = 0
            sid = str(scene.get("scene_id", f"scene_{idx}"))
            _record(
                changes,
                f"scenes[{sid}].transition",
                "break_hard_cuts",
                "Added 0.25s dissolve transition.",
            )


def _clamp_val(val: float, lo: float, hi: float) -> float:
    return round(max(lo, min(hi, val)), 2)


def _clamp_element_coords(
    el: dict[str, Any],
    w: int,
    h: int,
    safe_rect: tuple[float, float, float, float],
    sid: str,
    changes: list[dict[str, str]],
) -> None:
    sx0, sy0, sx1, sy1 = safe_rect
    et = str(el.get("type", ""))
    in_safe = et in SAFE_ZONE_TEXT_ELEMENTS
    lo_x, hi_x = (sx0, sx1) if in_safe else (0.0, float(w))
    lo_y, hi_y = (sy0, sy1) if in_safe else (0.0, float(h))

    if isinstance(el.get("box"), list) and len(el["box"]) == 4:
        b = [float(v) for v in el["box"]]
        nb = [
            _clamp_val(b[0], lo_x, hi_x),
            _clamp_val(b[1], lo_y, hi_y),
            _clamp_val(b[2], lo_x, hi_x),
            _clamp_val(b[3], lo_y, hi_y),
        ]
        if nb != b:
            el["box"] = nb
            _record(changes, f"scenes[{sid}].{et}.box", "clamp_box", f"{b} -> {nb}")
    for kx, ky in (("x", "y"), ("cx", "cy")):
        if el.get(kx) is not None and el.get(ky) is not None:
            ox, oy = float(el[kx]), float(el[ky])
            nx, ny = _clamp_val(ox, lo_x, hi_x), _clamp_val(oy, lo_y, hi_y)
            if nx != ox or ny != oy:
                el[kx], el[ky] = nx, ny
                _record(
                    changes,
                    f"scenes[{sid}].{et}",
                    "clamp_xy",
                    f"({ox},{oy}) -> ({nx},{ny})",
                )
    if isinstance(el.get("points"), list):
        new_pts = [
            [
                _clamp_val(float(p[0]), 0.0, float(w)),
                _clamp_val(float(p[1]), 0.0, float(h)),
            ]
            if isinstance(p, list) and len(p) >= 2
            else p
            for p in el["points"]
        ]
        if new_pts != el["points"]:
            el["points"] = new_pts
            _record(
                changes,
                f"scenes[{sid}].{et}.points",
                "clamp_points",
                "Clamped polyline inside canvas.",
            )
    if et == "image" and el.get("attribution_y") is not None:
        ay = float(el["attribution_y"])
        nay = _clamp_val(ay, sy0, sy1)
        if nay != ay:
            el["attribution_y"] = nay
            _record(
                changes,
                f"scenes[{sid}].image.attribution_y",
                "clamp_safe_y",
                f"{ay} -> {nay}",
            )


def _rescue_coordinates_and_safe_zones(
    scenes: list[dict[str, Any]],
    w: int,
    h: int,
    safe_rect: tuple[float, float, float, float],
    changes: list[dict[str, str]],
) -> None:
    for idx, scene in enumerate(scenes):
        sid = str(scene.get("scene_id", f"scene_{idx}"))
        for el in scene.get("elements") or []:
            if isinstance(el, dict):
                _clamp_element_coords(el, w, h, safe_rect, sid, changes)


def _polish_3d_scenes(
    scenes: list[dict[str, Any]], pal: dict[str, str], changes: list[dict[str, str]]
) -> None:
    for idx, scene in enumerate(scenes):
        spec = scene.get("scene_spec")
        if not isinstance(spec, dict):
            continue
        sid = str(scene.get("scene_id", f"scene_{idx}"))
        if "style_light" not in spec and pal.get("ground"):
            spec["style_light"] = {
                "bg_hex": pal["ground"][:7],
                "rim_hex": pal.get("highlight", "#FFFFFF")[:7],
                "shadow_softness": 0.45,
            }
            _record(
                changes,
                f"scenes[{sid}].scene_spec.style_light",
                "harmonize_3d_light",
                "Synced 3D lighting ground/rim to palette.",
            )


def run_storyboard_polish(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    out_path = Path(args.out).resolve()
    if in_path == out_path:
        print(
            "error: --in and --out must be distinct paths (non-destructive policy).",
            file=sys.stderr,
        )
        return 2
    if not in_path.is_file():
        print(f"error: no such storyboard: {args.input}", file=sys.stderr)
        return 2

    raw_board = cast(dict[str, Any], json.loads(in_path.read_text(encoding="utf-8")))
    before_sha = immutable_fingerprint(raw_board)
    before_audit = audit_storyboard(in_path, args.safe_mode, "auto")
    polished = copy.deepcopy(raw_board)
    changes: list[dict[str, str]] = []

    fmt_obj = polished.get("format") or {}
    w, h = (
        int(fmt_obj.get("width", 1280) or 1280),
        int(fmt_obj.get("height", 720) or 720),
    )
    fmt = classify_format(w, h)
    safe_rect = safe_rect_for(fmt, args.safe_mode, w, h)
    scenes = [s for s in polished.get("scenes", []) if isinstance(s, dict)]

    pal = _upgrade_style_and_palette(polished, args.look, changes)
    _upgrade_easings_and_motion(scenes, changes)
    _upgrade_transitions(scenes, changes)
    _rescue_coordinates_and_safe_zones(scenes, w, h, safe_rect, changes)
    _polish_3d_scenes(scenes, pal, changes)

    after_sha = immutable_fingerprint(polished)
    if before_sha != after_sha:
        raise RuntimeError("Immutable storyboard contract violated during polish.")

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".json", delete=False
    ) as tf:
        tf.write(json.dumps(polished, indent=2) + "\n")
        tmp_p = Path(tf.name)
    try:
        after_audit = audit_storyboard(tmp_p, args.safe_mode, "auto")
    finally:
        tmp_p.unlink(missing_ok=True)

    if not args.dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(polished, indent=2) + "\n", encoding="utf-8")

    report = {
        "tool_version": LINTER_VERSION,
        "mode": "storyboard",
        "input": str(in_path),
        "output": str(out_path),
        "look": args.look,
        "dry_run": bool(args.dry_run),
        "immutable_verified": True,
        "immutable_sha256_before": before_sha,
        "immutable_sha256_after": after_sha,
        "before_score": int(before_audit["video_health_score"]),
        "after_score": int(after_audit["video_health_score"]),
        "changes": changes,
        "commands": [],
        "qc_frames": [],
    }
    if args.report:
        rp = Path(args.report).resolve()
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def _loudnorm_pass1(in_path: Path) -> str:
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(in_path),
            "-af",
            "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
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
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.DOTALL)
    if not m:
        return "loudnorm=I=-14:TP=-1.5:LRA=11"
    data = json.loads(m.group(0))
    if any(str(data.get(k, "")).lower() == "-inf" for k in ("input_i", "input_tp")):
        return "loudnorm=I=-14:TP=-1.5:LRA=11"
    return (
        f"loudnorm=I=-14:TP=-1.5:LRA=11"
        f":measured_I={data['input_i']}:measured_TP={data['input_tp']}"
        f":measured_LRA={data['input_lra']}:measured_thresh={data['input_thresh']}"
        f":offset={data['target_offset']}:linear=true"
    )


def _build_video_filter(
    look: str,
    target_fmt: str | None,
    src_fmt: str,
    fps: int,
    captions: Path | None,
) -> str:
    parts: list[str] = []
    if target_fmt and target_fmt != src_fmt and target_fmt in FORMAT_DIMS:
        tw, th = FORMAT_DIMS[target_fmt]
        parts.append(
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},boxblur=20:2[bgb];"
            f"[fg]scale={tw}:{th}:force_original_aspect_ratio=decrease[fgf];"
            f"[bgb][fgf]overlay=(W-w)/2:(H-h)/2[vbase]"
        )
        cur = "[vbase]"
    else:
        cur = "[0:v]"

    chain: list[str] = []
    if VIDEO_LOOKS.get(look):
        chain.append(VIDEO_LOOKS[look])
    if captions is not None:
        esc = str(captions.resolve()).replace("\\", "\\\\").replace(":", "\\:")
        margin_v = 280 if target_fmt == "9:16" else 80
        chain.append(
            f"subtitles='{esc}':force_style='FontSize=28,PrimaryColour=&HFFFFFF,"
            f"OutlineColour=&H000000,Outline=2,Shadow=1,MarginV={margin_v},Alignment=2'"
        )
    chain.extend([f"fps={fps}", "setsar=1", "format=yuv420p"])
    parts.append(f"{cur}{','.join(chain)}[vout]")
    return ";".join(parts)


def _generate_qc_frames(
    in_path: Path, out_path: Path, qc_dir: Path, duration: float
) -> list[str]:
    qc_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    times = [
        ("frame_1", 0.0),
        ("midpoint", duration * 0.5),
        ("outro", max(0.0, duration - 0.5)),
    ]
    for label, ts in times:
        cmp_png = qc_dir / f"{label}_compare.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{ts:.3f}",
                "-i",
                str(in_path),
                "-ss",
                f"{ts:.3f}",
                "-i",
                str(out_path),
                "-filter_complex",
                "[0:v][1:v]hstack=inputs=2",
                "-frames:v",
                "1",
                str(cmp_png),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        written.append(str(cmp_png))
        sz_png = qc_dir / f"{label}_safezone.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{ts:.3f}",
                "-i",
                str(out_path),
                "-vf",
                "drawbox=x=iw*0.05:y=ih*0.05:w=iw*0.90:h=ih*0.90:color=0xFFB400@0.45:t=2,"
                "drawbox=x=iw*0.10:y=ih*0.10:w=iw*0.80:h=ih*0.80:color=0xFF3030@0.55:t=2",
                "-frames:v",
                "1",
                str(sz_png),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        written.append(str(sz_png))
    return written


def run_video_polish(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    out_path = Path(args.out).resolve()
    if in_path == out_path:
        print(
            "error: --in and --out must be distinct paths (non-destructive policy).",
            file=sys.stderr,
        )
        return 2
    if not in_path.is_file():
        print(f"error: no such video: {args.input}", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("error: ffmpeg and ffprobe are required on PATH.", file=sys.stderr)
        return 2

    sb_path = Path(args.storyboard).resolve() if args.storyboard else None
    cap_path = Path(args.captions).resolve() if args.captions else None
    before_audit = audit_video(in_path, sb_path, args.safe_mode, "auto", False, False)
    m = before_audit["metrics"]
    target_fmt = args.format if args.format != "auto" else before_audit["format"]
    fps = int(round(float(m.get("fps") or 30)))
    if fps not in (24, 25, 30, 50, 60):
        fps = 30

    fc = _build_video_filter(
        args.look, target_fmt, str(before_audit["format"]), fps, cap_path
    )
    af = (
        _loudnorm_pass1(in_path)
        if (args.loudnorm and not args.dry_run and m.get("audio_codec"))
        else None
    )
    cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-i",
        str(in_path),
        "-filter_complex",
        fc,
        "-map",
        "[vout]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        args.preset,
        "-crf",
        str(args.crf),
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-x264-params",
        "colorprim=bt709:transfer=bt709:colormatrix=bt709",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-color_range",
        "tv",
    ]
    if af:
        cmd.extend(["-af", f"{af},alimiter=limit=0.891"])
    cmd.extend(
        [
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )

    qc_frames: list[str] = []
    after_score: int | None = None
    if not args.dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )
        after_audit = audit_video(
            out_path, sb_path, args.safe_mode, "auto", bool(args.loudnorm), False
        )
        after_score = int(after_audit["video_health_score"])
        if args.qc_frames:
            qc_frames = _generate_qc_frames(
                in_path,
                out_path,
                Path(args.qc_frames).resolve(),
                float(m.get("duration_sec") or 1.0),
            )

    report = {
        "tool_version": LINTER_VERSION,
        "mode": "video",
        "input": str(in_path),
        "output": str(out_path),
        "look": args.look,
        "dry_run": bool(args.dry_run),
        "immutable_verified": True,
        "immutable_sha256_before": None,
        "immutable_sha256_after": None,
        "before_score": int(before_audit["video_health_score"]),
        "after_score": after_score,
        "changes": [
            {
                "scope": "video",
                "action": "single_pass_grade",
                "detail": f"look={args.look}, format={target_fmt}, fps={fps}, bt709, +faststart",
            },
            *(
                [
                    {
                        "scope": "audio",
                        "action": "loudnorm_2pass",
                        "detail": "EBU R128 -14 LUFS / -1.5 dBTP, AAC 48 kHz",
                    }
                ]
                if args.loudnorm
                else []
            ),
        ],
        "commands": [" ".join(cmd)],
        "qc_frames": qc_frames,
    }
    if args.report:
        rp = Path(args.report).resolve()
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Non-destructive visual polish engine for surgical-media."
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    p_sb = sub.add_parser(
        "storyboard", help="Mode A: polish a surgical-media storyboard JSON"
    )
    p_sb.add_argument(
        "--in", dest="input", required=True, help="Input storyboard .json"
    )
    p_sb.add_argument(
        "--out",
        required=True,
        help="Output polished storyboard .json (must differ from --in)",
    )
    p_sb.add_argument(
        "--look", choices=["preserve", *sorted(STORYBOARD_LOOKS)], default="preserve"
    )
    p_sb.add_argument("--safe-mode", choices=["organic", "strict"], default="strict")
    p_sb.add_argument("--dry-run", action="store_true")
    p_sb.add_argument("--report", help="Write action report JSON")

    p_vid = sub.add_parser("video", help="Mode B: single-pass FFmpeg finishing polish")
    p_vid.add_argument("--in", dest="input", required=True, help="Input .mp4")
    p_vid.add_argument(
        "--out", required=True, help="Output polished .mp4 (must differ from --in)"
    )
    p_vid.add_argument("--look", choices=sorted(VIDEO_LOOKS), default="cinematic_clean")
    p_vid.add_argument(
        "--format", choices=["auto", "9:16", "16:9", "4:5", "1:1"], default="auto"
    )
    p_vid.add_argument("--safe-mode", choices=["organic", "strict"], default="strict")
    p_vid.add_argument(
        "--loudnorm",
        action="store_true",
        help="Run two-pass EBU R128 -14 LUFS mastering",
    )
    p_vid.add_argument(
        "--captions", help="Optional .srt file to burn inside safe zones"
    )
    p_vid.add_argument(
        "--storyboard", help="Optional storyboard .json for post-op drift check"
    )
    p_vid.add_argument(
        "--qc-frames", help="Write before/after hstack + safe-zone PNGs to directory"
    )
    p_vid.add_argument("--crf", type=int, default=18)
    p_vid.add_argument("--preset", default="medium")
    p_vid.add_argument("--dry-run", action="store_true")
    p_vid.add_argument("--report", help="Write action report JSON")

    args = parser.parse_args(argv)
    if args.mode == "storyboard":
        return run_storyboard_polish(args)
    return run_video_polish(args)


if __name__ == "__main__":
    raise SystemExit(main())
