#!/usr/bin/env python3
"""
preflight_visual_lint.py — Zero-mutation static UI/GUI & rendering linter.

Inspects frontend codebases (CSS, SCSS, SASS, LESS, HTML, JS/TS, JSX/TSX,
Svelte, Vue, Python/Pygame/Qt, GDScript) for rendering bottlenecks, layout
thrashing, numeric jitter, WCAG 2.2 compliance gaps, and Three.js/WebGL hazards.

Usage:
    python3 scripts/preflight_visual_lint.py <target_dir> [--json | --sarif] [--out report.json] [--fail-on high] [--strict]

All operations are strictly read-only on target sources.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Defect Definitions & Regex Patterns
# ---------------------------------------------------------------------------

RE_LAYOUT_ANIM = re.compile(
    r"(?:transition(?:-property)?)\s*:[^;\n]*(?:^|[\s,:])"
    r"(?:width|height|top|left|right|bottom|margin(?:-(?:top|right|bottom|left))?|padding(?:-(?:top|right|bottom|left))?)\b"
    r"|animation\s*:[^;\n]*(?<![-\w])(?:width|height|top|left|right|bottom|margin|padding)(?![-\w])",
    re.IGNORECASE,
)
RE_KEYFRAME_LAYOUT_PROP = re.compile(
    r"(?:^|[\s;{])(?:width|height|top|left|right|bottom|margin(?:-(?:top|right|bottom|left))?|padding(?:-(?:top|right|bottom|left))?)\s*:",
    re.IGNORECASE,
)
RE_TABULAR_NUMS = re.compile(r"tabular-nums|tnum", re.IGNORECASE)
RE_TEXT_WRAP_BALANCE = re.compile(
    r"text-?wrap(?:-style)?\s*[:=]\s*['\"]?balance['\"]?",
    re.IGNORECASE,
)
RE_DYNAMIC_METRIC = re.compile(
    r"(?:counter|timer|telemetry|stat-value|metric|live-data|readout|price|balance|fps)",
    re.IGNORECASE,
)
RE_BACKDROP_BLUR = re.compile(r"backdrop-filter\s*:\s*blur\(([^)]+)\)", re.IGNORECASE)

# Matches property assignment lerps (e.g. this.x += (target - this.x) * 0.1)
RE_FIXED_LERP_ASSIGN = re.compile(
    r"([\w.]+)\s*\+=\s*\([^)]*-\s*\1\)\s*\*\s*0\.\d+",
    re.IGNORECASE,
)
# Matches direct lerp / slerp / lerpVectors calls with constant multipliers:
# both 2-arg (v.lerp(target, 0.1) / q.slerp(targetQ, 0.1)) and 3-arg (lerp(a, b, 0.1))
RE_FIXED_LERP_FN = re.compile(
    r"(?:\.\s*(?:lerp|slerp)\s*\([^\n,]+,\s*0\.\d+\s*\)"
    r"|\b(?:lerp|slerp|lerpVectors)\s*\([^\n,]+,[^\n,]+,\s*0\.\d+\s*\))",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# WCAG 2.2 patterns
# ---------------------------------------------------------------------------

RE_CSS_SIZE_DECL = re.compile(
    r"(?:^|[\s;{])((?:min-)?(?:width|height))\s*:\s*(\d+(?:\.\d+)?)\s*px\b",
    re.IGNORECASE,
)
RE_INLINE_INTERACTIVE_TAG = re.compile(
    r"<(?:button|a|summary|input)\b[^>]*\bstyle\s*=\s*(?:\{\{([^}]*)\}\}|[\"']([^\"']*)[\"'])",
    re.IGNORECASE,
)
RE_JSX_NUM_SIZE = re.compile(
    r"\b((?:min)?(?:width|height))\s*:\s*(?:['\"](\d+(?:\.\d+)?)\s*px['\"]|(\d+(?:\.\d+)?)\b)",
    re.IGNORECASE,
)
RE_INTERACTIVE_SELECTOR = re.compile(
    r"(?:\b(?:button|a|input|select|textarea|summary)\b|role\s*=\s*['\"]?button['\"]?"
    r"|(?:btn|button|close|toggle|tab|chip|nav-link|menu-item|control|trigger))",
    re.IGNORECASE,
)
RE_NON_INTERACTIVE_DECOR = re.compile(
    r"(?:::before|::after|spinner|divider|border|badge|\bdot\b|\bpip\b|sr-only)",
    re.IGNORECASE,
)
RE_STICKY_HEADER_CSS = re.compile(
    r"position\s*:\s*(?:sticky|fixed)",
    re.IGNORECASE,
)
RE_STICKY_HEADER_SELECTOR = re.compile(
    r"\b(?:nav|navbar|header|topbar|toolbar|appbar|banner)\b",
    re.IGNORECASE,
)
RE_STICKY_TAILWIND = re.compile(
    r"(?:\b(?:sticky|fixed)\b[^\n\"'>]*\btop-0\b|\btop-0\b[^\n\"'>]*\b(?:sticky|fixed)\b)",
    re.IGNORECASE,
)
RE_SCROLL_MARGIN_TOP = re.compile(
    r"scroll-(?:margin|padding)-top|scroll(?:Margin|Padding)Top|\bscroll-(?:mt|pt)-",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Three.js / WebGL 3D patterns
# ---------------------------------------------------------------------------

RE_SET_PIXEL_RATIO = re.compile(r"setPixelRatio\s*\(\s*([^)]*)\)")
RE_PIXEL_RATIO_UNCLAMPED = re.compile(r"devicePixelRatio", re.IGNORECASE)
RE_PIXEL_RATIO_CLAMPED = re.compile(r"Math\.(?:min|max)|clamp", re.IGNORECASE)

RE_THREE_SCRATCH_ALLOC = re.compile(
    r"new\s+(?:THREE\.)?(Vector[234]|Quaternion|Euler|Color|Matrix4)\s*\(\s*\)"
)
RE_THREE_RENDER_LOOP = re.compile(
    r"requestAnimationFrame|setAnimationLoop|onBeforeRender"
)
RE_THREE_CAST_SHADOW = re.compile(r"castShadow\s*=\s*true")
RE_THREE_SHADOW_BIAS = re.compile(r"\.bias\s*=|normalBias")
# HemisphereLight and RectAreaLight do not cast shadows in Three.js.
RE_THREE_LIGHT_CREATION = re.compile(
    r"new\s+(?:THREE\.)?(DirectionalLight|PointLight|SpotLight|SunLight)\s*\("
)
RE_THREE_RENDERER = re.compile(r"new\s+(?:THREE\.)?WebGLRenderer\s*\(")
RE_THREE_RENDERER_ASSIGN = re.compile(
    r"(?:(?:const|let|var)\s+([A-Za-z_$][\w$]*)|((?:this\.)?[A-Za-z_$][\w$]*))\s*=\s*"
    r"new\s+(?:THREE\.)?WebGLRenderer\s*\("
)
RE_THREE_OUTPUT_COLOR_SPACE = re.compile(r"outputColorSpace")
RE_THREE_GLTF_LOADER = re.compile(r"new\s+(?:THREE\.)?GLTFLoader\s*\(")
RE_THREE_DECODERS = re.compile(r"DRACOLoader|MeshoptDecoder|KTX2Loader")
RE_THREE_RESIZE = re.compile(
    r"addEventListener\s*\(\s*['\"]resize['\"]|ResizeObserver|\.setSize\s*\("
)
RE_THREE_PROJECT = re.compile(
    r"from\s+['\"]three(?:/[^'\"]*)?['\"]|require\s*\(\s*['\"]three['\"]\s*\)|\bTHREE\.",
    re.IGNORECASE,
)

# --- Scope analysis (so a rule can tell module scope from a frame callback) ---
RE_CONSTRUCTOR = re.compile(r"\bconstructor\s*\(")
RE_STRING_OR_COMMENT = re.compile(
    r"//[^\n]*|/\*.*?\*/|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`",
    re.DOTALL,
)
BLOCK_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "do",
    "try",
    "finally",
    "else",
    "return",
    "typeof",
    "new",
    "delete",
    "void",
    "await",
    "yield",
    "case",
    "default",
    "in",
    "of",
    "super",
    "this",
    "with",
    "enum",
    "const",
    "let",
    "var",
    "function",
    "import",
    "export",
}
RE_METHOD_HEADER = re.compile(
    r"^(?:(?:public|private|protected|static|async|override|readonly|get|set)\s+)*"
    r"(?:[A-Za-z_$][\w$]*\.)*([A-Za-z_$][\w$]*)"
    r"(?:\s*<[^<>]*>)?\s*\([^()]*\)\s*(?::\s*[^=;{}]+)?$"
)
RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def blank_block_comments(text: str) -> str:
    """Remove /* ... */ blocks while preserving line numbers."""
    return RE_BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def blank_strings_and_comments(text: str) -> str:
    """Remove strings, template literals, and comments whole-file while preserving line numbers."""
    return RE_STRING_OR_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


JS_EXTS = {".js", ".jsx", ".ts", ".tsx"}
STYLE_EXTS = {".css", ".scss", ".sass", ".less"}
MARKUP_EXTS = {".html", ".jsx", ".tsx", ".svelte", ".vue"}
SUPPORTED_EXTS = STYLE_EXTS | MARKUP_EXTS | {".js", ".ts", ".py", ".gd"}

EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    ".svelte-kit",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "coverage",
    "playwright-report",
    "test-results",
    "venv",
}

# Keep in sync with SKILL.md `version:` — the linter advertises it.
LINTER_VERSION = "1.4.0"

SEVERITY_WEIGHTS = {
    "HIGH": 10,
    "MEDIUM": 5,
    "LOW": 2,
}

SEVERITY_ORDER = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
}

SARIF_SCHEMA = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
SARIF_LEVELS = {
    "HIGH": "error",
    "MEDIUM": "warning",
    "LOW": "note",
}


def _strip_balanced_parens(text: str) -> str:
    """Collapse nested parenthesized argument lists to `()` so RE_METHOD_HEADER stays simple."""
    out: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            if depth == 0:
                out.append("(")
            depth += 1
        elif ch == ")":
            if depth > 0:
                depth -= 1
                if depth == 0:
                    out.append(")")
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _has_renderer_dispose(code: str) -> bool:
    """Verify the constructed WebGLRenderer instance itself is disposed (not just pmrem.dispose())."""
    renderer_vars: list[str] = []
    for match in RE_THREE_RENDERER_ASSIGN.finditer(code):
        var_name = match.group(1) or match.group(2)
        if var_name:
            renderer_vars.append(var_name)
    if renderer_vars:
        return any(
            re.search(rf"\b{re.escape(name)}\.dispose\s*\(", code)
            for name in renderer_vars
        )
    # Fallback for anonymous `new THREE.WebGLRenderer()` construction:
    # ignore helper-only disposals such as `pmrem.dispose()`.
    for match in re.finditer(r"([A-Za-z_$][\w$.]*)\.dispose\s*\(", code):
        target = match.group(1).lower()
        if "pmrem" not in target and "env" not in target:
            return True
    return False


# ---------------------------------------------------------------------------
# Scanner Engine
# ---------------------------------------------------------------------------


class VisualAuditor:
    def __init__(self, root_dir: str) -> None:
        self.root_dir = os.path.abspath(root_dir)
        self.files_scanned = 0
        self.total_loc = 0
        self.unreadable = 0
        self.defects: list[dict[str, Any]] = []
        self.has_reduced_motion = False
        self.reduced_motion_loc: tuple[str, int] | None = None
        self.has_prefers_contrast = False
        self.has_forced_colors = False
        self.has_motion = False
        self.has_sticky_header = False
        self.sticky_header_loc: tuple[str, int] | None = None
        self.has_scroll_margin_top = False

    def _add_defect(
        self, file: str, line: int, code: str, severity: str, message: str, fix: str
    ) -> None:
        self.defects.append(
            {
                "file": file,
                "line": line,
                "code": code,
                "severity": severity,
                "message": message,
                "fix": fix,
            }
        )

    def scan(self) -> dict[str, Any]:
        if not os.path.exists(self.root_dir):
            raise FileNotFoundError(f"target path does not exist: {self.root_dir}")

        if os.path.isfile(self.root_dir):
            ext = os.path.splitext(self.root_dir)[1].lower()
            if ext in SUPPORTED_EXTS:
                self._scan_file(self.root_dir, ext)
        else:
            for root, dirs, files in os.walk(self.root_dir):
                dirs[:] = sorted(
                    d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")
                )
                for file in sorted(files):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in SUPPORTED_EXTS:
                        self._scan_file(os.path.join(root, file), ext)

        self._check_project_guards()

        penalty = sum(SEVERITY_WEIGHTS.get(d["severity"], 2) for d in self.defects)
        score = max(0, 100 - penalty)
        sorted_defects = sorted(
            self.defects, key=lambda d: SEVERITY_ORDER.get(d["severity"], 99)
        )

        return {
            "target_dir": self.root_dir,
            "files_scanned": self.files_scanned,
            "unreadable_files": self.unreadable,
            "total_loc": self.total_loc,
            "visual_health_score": score,
            "defects_count": len(self.defects),
            "defects": sorted_defects,
        }

    def _check_project_guards(self) -> None:
        if self.files_scanned <= 0:
            return

        if self.has_motion and not self.has_reduced_motion:
            self._add_defect(
                "Global Stylesheet / Media Queries",
                1,
                "MISSING_REDUCED_MOTION_GUARD",
                "HIGH",
                "Animations or transitions detected across project but zero @media (prefers-reduced-motion) declarations found.",
                "Add @media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; } .btn-spinner { animation-duration: 1.5s !important; } }",
            )

        if self.has_reduced_motion and (
            not self.has_prefers_contrast or not self.has_forced_colors
        ):
            missing: list[str] = []
            if not self.has_prefers_contrast:
                missing.append("@media (prefers-contrast: more)")
            if not self.has_forced_colors:
                missing.append("@media (forced-colors: active)")
            loc_file, loc_line = self.reduced_motion_loc or (
                "Global Stylesheet / Media Queries",
                1,
            )
            self._add_defect(
                loc_file,
                loc_line,
                "WCAG_MISSING_CONTRAST_OR_FORCED_COLORS",
                "LOW",
                f"prefers-reduced-motion is declared without companion {', '.join(missing)} accessibility media query.",
                "Pair @media (prefers-reduced-motion: reduce) with @media (prefers-contrast: more) and @media (forced-colors: active).",
            )

        if self.has_sticky_header and not self.has_scroll_margin_top:
            loc_file, loc_line = self.sticky_header_loc or (
                "Global Stylesheet / Media Queries",
                1,
            )
            self._add_defect(
                loc_file,
                loc_line,
                "WCAG_STICKY_FOCUS_OBSCURED",
                "MEDIUM",
                "Sticky/fixed top header or nav detected without scroll-margin-top / scroll-padding-top (WCAG 2.2 SC 2.4.11 Focus Not Obscured).",
                "Set scroll-margin-top (or scroll-padding-top on html) >= the sticky header height so anchored headings and focused controls remain unobscured.",
            )

    def _update_preference_flags(self, rel_path: str, content: str) -> None:
        if "prefers-reduced-motion" in content:
            self.has_reduced_motion = True
            if self.reduced_motion_loc is None:
                for idx, line in enumerate(content.splitlines(), 1):
                    if "prefers-reduced-motion" in line:
                        self.reduced_motion_loc = (rel_path, idx)
                        break
        if "prefers-contrast" in content:
            self.has_prefers_contrast = True
        if "forced-colors" in content:
            self.has_forced_colors = True
        if RE_SCROLL_MARGIN_TOP.search(content):
            self.has_scroll_margin_top = True
        if re.search(r"\b(?:transition|animation)\s*:", content, re.IGNORECASE):
            self.has_motion = True

    def _scan_file(self, path: str, ext: str) -> None:
        base_dir = (
            os.path.dirname(self.root_dir)
            if os.path.isfile(self.root_dir)
            else self.root_dir
        )
        rel_path = os.path.relpath(path, base_dir)
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError as exc:
            self.unreadable += 1
            self._add_defect(
                rel_path,
                0,
                "UNREADABLE_SOURCE",
                "MEDIUM",
                f"Could not read file: {exc}",
                "Fix file permissions or exclude the path explicitly.",
            )
            return

        self.files_scanned += 1
        lines = content.splitlines()
        self.total_loc += len(lines)
        self._update_preference_flags(rel_path, content)

        is_three = ext in JS_EXTS and bool(RE_THREE_PROJECT.search(content))
        stripped_text = blank_strings_and_comments(content)
        code_lines = stripped_text.splitlines()
        has_render_loop = bool(RE_THREE_RENDER_LOOP.search(stripped_text))
        scope_map, alloc_in_func = (
            self._analyze_three_scopes(code_lines) if is_three else ([], set())
        )

        self._scan_lines(
            rel_path, ext, lines, code_lines, is_three, has_render_loop, alloc_in_func
        )
        if ext in STYLE_EXTS or ext in MARKUP_EXTS:
            self._scan_wcag_css_and_markup(rel_path, ext, content)
        if is_three:
            self._scan_three_file(rel_path, code_lines)
        # Keep _scope_map usable by tests/callers even though _analyze_three_scopes handles inline scopes
        _ = scope_map

    def _check_keyframes_line(
        self,
        rel_path: str,
        idx: int,
        stripped: str,
        in_keyframes: bool,
        kf_depth: int,
    ) -> tuple[bool, int]:
        if "@keyframes" in stripped.lower():
            in_keyframes = True
            kf_depth = 0
        if not in_keyframes:
            return False, 0
        kf_depth += stripped.count("{") - stripped.count("}")
        if RE_KEYFRAME_LAYOUT_PROP.search(stripped):
            self._add_defect(
                rel_path,
                idx,
                "LAYOUT_THRASHING_ANIMATION",
                "HIGH",
                f"@keyframes animates layout property: '{stripped[:70]}'.",
                "Animate compositor-only properties ('transform', 'opacity') instead of box-model properties.",
            )
        if kf_depth <= 0 and "}" in stripped:
            in_keyframes = False
        return in_keyframes, kf_depth

    def _check_motion_and_metric_line(
        self,
        rel_path: str,
        ext: str,
        lines: list[str],
        idx: int,
        line: str,
        stripped: str,
    ) -> None:
        m_layout = RE_LAYOUT_ANIM.search(line)
        if m_layout:
            self._add_defect(
                rel_path,
                idx,
                "LAYOUT_THRASHING_ANIMATION",
                "HIGH",
                f"Transition/animation triggers layout reflow: '{m_layout.group(0).strip()}'.",
                "Animate compositor-only properties ('transform', 'opacity') using CSS scale/translate or matrix3d.",
            )

        m_blur = RE_BACKDROP_BLUR.search(line)
        if m_blur:
            px_match = re.search(r"(\d+)\s*px", m_blur.group(1).strip())
            if px_match and int(px_match.group(1)) > 16:
                self._add_defect(
                    rel_path,
                    idx,
                    "EXCESSIVE_BLUR_OVERDRAW",
                    "MEDIUM",
                    f"backdrop-filter blur radius ({px_match.group(1)}px) exceeds safe 16px frame budget.",
                    "Clamp blur radius <= 16px and ensure maximum 2 overlapping blur layers.",
                )

        m_lerp = RE_FIXED_LERP_ASSIGN.search(line) or RE_FIXED_LERP_FN.search(line)
        if m_lerp and ext in {".js", ".ts", ".jsx", ".tsx", ".py", ".gd"}:
            self._add_defect(
                rel_path,
                idx,
                "FRAME_RATE_DEPENDENT_LERP",
                "HIGH",
                f"Fixed multiplier animation loop '{m_lerp.group(0)}' runs at variable speeds on 60Hz vs 120Hz.",
                "Use delta-time exponential decay: expDecay(current, target, decay, dt) or stepSpringSubstepped().",
            )

        cleaned_for_metric = RE_TEXT_WRAP_BALANCE.sub("", line)
        if (
            ext in MARKUP_EXTS
            and RE_DYNAMIC_METRIC.search(cleaned_for_metric)
            and not RE_TABULAR_NUMS.search(line)
        ):
            snippet = "\n".join(lines[max(0, idx - 5) : min(len(lines), idx + 5)])
            if not RE_TABULAR_NUMS.search(snippet):
                self._add_defect(
                    rel_path,
                    idx,
                    "NUMERIC_JITTER_HAZARD",
                    "LOW",
                    f"Dynamic counter/metric readout element may lack tabular-nums: '{stripped[:60]}'.",
                    "Apply font-variant-numeric: tabular-nums; to prevent horizontal number oscillation.",
                )

    def _check_three_line(
        self,
        rel_path: str,
        idx: int,
        line: str,
        stripped: str,
        code_line: str,
        has_render_loop: bool,
        alloc_in_func: set[int],
    ) -> None:
        m_pr = RE_SET_PIXEL_RATIO.search(line)
        if m_pr:
            arg = m_pr.group(1)
            if RE_PIXEL_RATIO_UNCLAMPED.search(
                arg
            ) and not RE_PIXEL_RATIO_CLAMPED.search(arg):
                self._add_defect(
                    rel_path,
                    idx,
                    "THREE_UNCLAMPED_PIXEL_RATIO",
                    "HIGH",
                    f"setPixelRatio() uses the raw devicePixelRatio without a clamp: '{stripped[:70]}'.",
                    "Clamp the buffer scale: renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)).",
                )

        if (
            has_render_loop
            and RE_THREE_SCRATCH_ALLOC.search(code_line)
            and idx in alloc_in_func
        ):
            self._add_defect(
                rel_path,
                idx,
                "THREE_PER_FRAME_ALLOCATION",
                "MEDIUM",
                f"Scratch object allocated with no arguments inside a function: '{code_line.strip()[:70]}'. In a per-frame callback this is GC pressure.",
                "Hoist reusable scratch vectors/quaternions to module scope and mutate them in place (v.copy(...), q.setFromEuler(...)).",
            )

    def _scan_lines(
        self,
        rel_path: str,
        ext: str,
        lines: list[str],
        code_lines: list[str],
        is_three: bool,
        has_render_loop: bool,
        alloc_in_func: set[int],
    ) -> None:
        in_keyframes = False
        kf_depth = 0

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("#", "//", "/*", "*")):
                continue
            if ext in STYLE_EXTS or ext in MARKUP_EXTS:
                in_keyframes, kf_depth = self._check_keyframes_line(
                    rel_path, idx, stripped, in_keyframes, kf_depth
                )
            self._check_motion_and_metric_line(
                rel_path, ext, lines, idx, line, stripped
            )
            if is_three:
                code_line = code_lines[idx - 1] if idx - 1 < len(code_lines) else ""
                self._check_three_line(
                    rel_path,
                    idx,
                    line,
                    stripped,
                    code_line,
                    has_render_loop,
                    alloc_in_func,
                )

    def _scan_markup_wcag_line(self, rel_path: str, idx: int, line: str) -> None:
        if RE_STICKY_TAILWIND.search(line) and RE_STICKY_HEADER_SELECTOR.search(line):
            self.has_sticky_header = True
            if self.sticky_header_loc is None:
                self.sticky_header_loc = (rel_path, idx)
        for tag_m in RE_INLINE_INTERACTIVE_TAG.finditer(line):
            style_body = tag_m.group(1) or tag_m.group(2) or ""
            for sz_m in RE_JSX_NUM_SIZE.finditer(style_body):
                val = float(sz_m.group(2) or sz_m.group(3))
                if 0 < val < 24:
                    self._add_defect(
                        rel_path,
                        idx,
                        "WCAG_SMALL_TARGET_SIZE",
                        "MEDIUM",
                        f"Interactive element sets {sz_m.group(1)} to {val:g}px (< 24px minimum; WCAG 2.2 SC 2.5.8).",
                        "Ensure interactive hit targets are at least 24x24 CSS px (>= 44x44 px under any-pointer: coarse).",
                    )
                    break

    def _scan_wcag_css_and_markup(self, rel_path: str, ext: str, content: str) -> None:
        clean_css_text = blank_block_comments(content)
        lines = clean_css_text.splitlines()
        selector_buf: list[str] = []
        block_stack: list[str] = []

        for idx, line in enumerate(lines, 1):
            if ext in MARKUP_EXTS:
                self._scan_markup_wcag_line(rel_path, idx, line)

            # Track CSS rules (also applies inside <style> tags)
            if "{" in line:
                before_brace, after_brace = line.split("{", 1)
                selector = (" ".join(selector_buf) + " " + before_brace).strip()
                selector_buf.clear()
                block_stack.append(selector)
                self._inspect_css_rule_line(rel_path, idx, selector, after_brace)
            elif "}" in line:
                if block_stack:
                    self._inspect_css_rule_line(
                        rel_path, idx, block_stack[-1], line.split("}", 1)[0]
                    )
                    block_stack.pop()
                selector_buf.clear()
            elif block_stack:
                self._inspect_css_rule_line(rel_path, idx, block_stack[-1], line)
            else:
                stripped = line.strip()
                if stripped and not stripped.startswith("<"):
                    selector_buf.append(stripped)

    def _inspect_css_rule_line(
        self, rel_path: str, line_no: int, selector: str, decl: str
    ) -> None:
        if RE_STICKY_HEADER_CSS.search(decl) and RE_STICKY_HEADER_SELECTOR.search(
            selector
        ):
            self.has_sticky_header = True
            if self.sticky_header_loc is None:
                self.sticky_header_loc = (rel_path, line_no)

        if RE_INTERACTIVE_SELECTOR.search(
            selector
        ) and not RE_NON_INTERACTIVE_DECOR.search(selector):
            for m_sz in RE_CSS_SIZE_DECL.finditer(decl):
                val = float(m_sz.group(2))
                if 0 < val < 24:
                    self._add_defect(
                        rel_path,
                        line_no,
                        "WCAG_SMALL_TARGET_SIZE",
                        "MEDIUM",
                        f"Interactive target '{selector[:50]}' declares {m_sz.group(1)}: {val:g}px (< 24px minimum; WCAG 2.2 SC 2.5.8).",
                        "Enlarge interactive controls to >= 24x24 CSS px (>= 44x44 px for any-pointer: coarse).",
                    )
                    break

    @staticmethod
    def _classify_block(header: str) -> str:
        """Classify the block a header opens: 'class' | 'ctor' | 'func' | 'block'."""
        h = header.strip()
        if not h or h.endswith(":"):
            return "block"
        if re.search(r"\bclass\b", h):
            return "class"
        if RE_CONSTRUCTOR.search(h):
            return "ctor"
        first_word = re.split(r"[\s(]+", h, maxsplit=1)[0]
        if first_word in BLOCK_KEYWORDS and first_word not in {"function", "async"}:
            return "block"
        if (
            re.search(r"\bfunction\b", h)
            or h.rstrip().endswith("=>")
            or "=>" in _strip_balanced_parens(h)
        ):
            return "func"
        normalized = _strip_balanced_parens(h)
        m = RE_METHOD_HEADER.search(normalized)
        if m and m.group(1) not in BLOCK_KEYWORDS:
            return "func"
        return "block"

    @staticmethod
    def _step_scope_char(
        ch: str, stack: list[str], paren: int, header_buf: list[str]
    ) -> int:
        if ch in "([":
            header_buf.append(ch)
            return paren + 1
        if ch in ")]":
            header_buf.append(ch)
            return max(0, paren - 1)
        if ch == "{":
            hdr = "".join(header_buf).strip()
            if paren == 0:
                kind = VisualAuditor._classify_block(hdr)
            elif hdr.endswith("=>"):
                kind = "func"
            else:
                kind = "block"
            header_buf.clear()
            stack.append(kind)
            return paren
        if ch == "}":
            if stack:
                stack.pop()
            if paren == 0:
                header_buf.clear()
            return paren
        if ch == ";" and paren == 0:
            header_buf.clear()
            return paren
        header_buf.append(ch)
        return paren

    @staticmethod
    def _analyze_three_scopes(
        code_lines: list[str],
    ) -> tuple[list[tuple[list[str], str | None]], set[int]]:
        """Analyze enclosing block scopes across all lines and inline `{` blocks.

        Returns `(scope_map_per_line, line_numbers_with_func_alloc)`.
        """
        stack: list[str] = []
        scope_out: list[tuple[list[str], str | None]] = []
        alloc_lines: set[int] = set()
        paren = 0
        header_buf: list[str] = []

        for line_no, line in enumerate(code_lines, 1):
            scope_out.append((list(stack), stack[-1] if stack else None))
            alloc_spans = [m.start() for m in RE_THREE_SCRATCH_ALLOC.finditer(line)]
            alloc_idx = 0
            for col, ch in enumerate(line):
                while alloc_idx < len(alloc_spans) and col == alloc_spans[alloc_idx]:
                    if "func" in stack and "ctor" not in stack:
                        alloc_lines.add(line_no)
                    alloc_idx += 1
                paren = VisualAuditor._step_scope_char(ch, stack, paren, header_buf)
            if paren == 0:
                header_buf.append(" ")

        return scope_out, alloc_lines

    @staticmethod
    def _scope_map(lines: list[str]) -> list[tuple[list[str], str | None]]:
        """Return [(stack_snapshot, innermost_kind)] per line."""
        code_lines = [RE_STRING_OR_COMMENT.sub("", line) for line in lines]
        scope_out, _ = VisualAuditor._analyze_three_scopes(code_lines)
        return scope_out

    def _flag_first_match(
        self,
        rel_path: str,
        code_lines: list[str],
        pattern: re.Pattern[str],
        code: str,
        severity: str,
        message: str,
        remediation: str,
    ) -> None:
        for idx, line in enumerate(code_lines, 1):
            if pattern.search(line):
                self._add_defect(rel_path, idx, code, severity, message, remediation)
                break

    def _scan_three_file(self, rel_path: str, code_lines: list[str]) -> None:
        """Three.js hazards that require whole-file context."""
        code = "\n".join(code_lines)
        has_renderer = bool(RE_THREE_RENDERER.search(code))

        if has_renderer and not _has_renderer_dispose(code):
            self._flag_first_match(
                rel_path,
                code_lines,
                RE_THREE_RENDERER,
                "THREE_MISSING_DISPOSE",
                "MEDIUM",
                "A WebGLRenderer is created here but the file never calls .dispose() on it — the WebGL context and its GPU resources leak on teardown.",
                "Call renderer.dispose() (and renderer.forceContextLoss() in dev) when the owning view unmounts.",
            )

        if (
            RE_THREE_LIGHT_CREATION.search(code)
            and RE_THREE_CAST_SHADOW.search(code)
            and not RE_THREE_SHADOW_BIAS.search(code)
        ):
            self._flag_first_match(
                rel_path,
                code_lines,
                RE_THREE_CAST_SHADOW,
                "THREE_MISSING_SHADOW_BIAS",
                "MEDIUM",
                "This file creates a shadow-casting light and enables castShadow but sets no shadow.bias / shadow.normalBias — shadow acne and peter-panning are likely.",
                "Tune the light: light.shadow.bias = -0.0004 and light.shadow.normalBias = 0.02 (scale normalBias to your world units).",
            )

        if has_renderer and not RE_THREE_OUTPUT_COLOR_SPACE.search(code):
            self._flag_first_match(
                rel_path,
                code_lines,
                RE_THREE_RENDERER,
                "THREE_UNSET_OUTPUT_COLOR_SPACE",
                "LOW",
                "WebGLRenderer created without an explicit outputColorSpace setting.",
                "Set renderer.outputColorSpace = THREE.SRGBColorSpace explicitly (default since r152, but pinning it prevents silent regressions).",
            )

        if RE_THREE_GLTF_LOADER.search(code) and not RE_THREE_DECODERS.search(code):
            self._flag_first_match(
                rel_path,
                code_lines,
                RE_THREE_GLTF_LOADER,
                "THREE_UNCOMPRESSED_GLTF",
                "LOW",
                "GLTFLoader is instantiated with no Draco / meshopt / KTX2 decoder — payloads stay 3-10x larger than necessary.",
                "Wire decoders: loader.setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder) and ktx2.detectSupport(renderer).",
            )

        if has_renderer and not RE_THREE_RESIZE.search(code):
            self._flag_first_match(
                rel_path,
                code_lines,
                RE_THREE_RENDERER,
                "THREE_MISSING_RESIZE_HANDLER",
                "LOW",
                "WebGLRenderer created with no resize listener or ResizeObserver.",
                "Handle resize: update camera.aspect + camera.updateProjectionMatrix() and renderer.setSize(w, h, false).",
            )


# ---------------------------------------------------------------------------
# Output formatters (Human / JSON / SARIF 2.1.0)
# ---------------------------------------------------------------------------


def build_sarif(results: dict[str, Any]) -> dict[str, Any]:
    """Convert visual audit results into a valid SARIF 2.1.0 payload."""
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
                                "uri": str(defect["file"]).replace(os.sep, "/"),
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
                        "name": "plastic-surgery-preflight-visual-lint",
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
    print(f" Plastic Surgery Preflight Visual Linter (v{LINTER_VERSION})")
    print(f" Target: {results['target_dir']}")
    print(
        f" Files Scanned: {results['files_scanned']} | Total LOC: {results['total_loc']}"
    )
    if results["unreadable_files"]:
        print(
            f" Unreadable Files: {results['unreadable_files']} (counted as MEDIUM defects)"
        )
    print(f" Visual Health Score: {results['visual_health_score']} / 100")
    print(f" Detected Defects: {results['defects_count']}")
    print("========================================================\n")

    if results["defects"]:
        for d in results["defects"][:20]:
            print(f"[{d['severity']}] {d['code']} at {d['file']}:{d['line']}")
            print(f"  Issue: {d['message']}")
            print(f"  Fix:   {d['fix']}\n")
        if len(results["defects"]) > 20:
            print(
                f"... and {len(results['defects']) - 20} more defects (see --out report.json)"
            )
    else:
        print("✓ Zero visual or compositor defects detected. Clean presentation skin!")

    if out_path:
        print(f"\nReport saved to: {out_path}")


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero-mutation UI/GUI visual linter.")
    parser.add_argument(
        "target_dir", nargs="?", default=".", help="Target repository or UI directory"
    )
    parser.add_argument("--out", help="Write audit report (JSON or SARIF) to file")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report to stdout",
    )
    parser.add_argument(
        "--sarif",
        action="store_true",
        help="Emit SARIF 2.1.0 report to stdout (and to --out if provided)",
    )
    parser.add_argument(
        "--fail-on",
        choices=["high", "medium", "low"],
        default=None,
        help="Exit 1 when a defect at or above this severity is present (CI gate).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any target file is unreadable.",
    )
    args = parser.parse_args()

    try:
        auditor = VisualAuditor(args.target_dir)
        results = auditor.scan()
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload: dict[str, Any] = build_sarif(results) if args.sarif else results

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    if args.sarif or args.json:
        print(json.dumps(payload, indent=2))
    else:
        _print_human_report(results, args.out)

    if args.strict and results["unreadable_files"] > 0:
        print(
            f"GATE FAILED (--strict): {results['unreadable_files']} unreadable source file(s).",
            file=sys.stderr,
        )
        return 1

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
