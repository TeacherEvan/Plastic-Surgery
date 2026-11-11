#!/usr/bin/env python3
"""
preflight_visual_lint.py — Zero-mutation static UI/GUI & rendering linter.

Inspects frontend codebases (CSS, SCSS, JS/TS, JSX/TSX, Svelte, Vue, Python/Pygame/Qt, GDScript)
for rendering bottlenecks, layout thrashing, numeric jitter, reduced-motion gaps, and tactile flaws.

Usage:
    python3 scripts/preflight_visual_lint.py <target_dir> [--out report.json]

All operations are strictly read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Defect Definitions & Regex Patterns
# ---------------------------------------------------------------------------

RE_LAYOUT_ANIM = re.compile(
    r"(?:transition|animation)\s*:[^;]*(?:width|height|top|left|right|bottom|margin|padding)",
    re.IGNORECASE,
)
RE_TABULAR_NUMS = re.compile(r"tabular-nums|tnum", re.IGNORECASE)
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
# Matches direct lerp function calls with constant multipliers (e.g. lerp(current, target, 0.1))
RE_FIXED_LERP_FN = re.compile(
    r"\blerp\s*\([^,]+,[^,]+,\s*0\.\d+\s*\)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Three.js / WebGL 3D patterns
# ---------------------------------------------------------------------------

# setPixelRatio(devicePixelRatio) without a clamp
RE_SET_PIXEL_RATIO = re.compile(r"setPixelRatio\s*\(\s*([^)]*)\)")
RE_PIXEL_RATIO_UNCLAMPED = re.compile(r"devicePixelRatio", re.IGNORECASE)
RE_PIXEL_RATIO_CLAMPED = re.compile(r"Math\.(?:min|max)|clamp", re.IGNORECASE)

# Zero-argument scratch-object allocation (new THREE.Vector3()) — GC pressure in a loop
RE_THREE_SCRATCH_ALLOC = re.compile(
    r"new\s+(?:THREE\.)?(Vector[234]|Quaternion|Euler|Color|Matrix4)\s*\(\s*\)"
)

# Resources that own GPU memory and therefore need an explicit dispose()
RE_THREE_DISPOSE = re.compile(r"\.dispose\s*\(")
RE_THREE_RENDER_LOOP = re.compile(r"requestAnimationFrame|setAnimationLoop|onBeforeRender")
RE_THREE_CAST_SHADOW = re.compile(r"castShadow\s*=\s*true")
RE_THREE_SHADOW_BIAS = re.compile(r"\.bias\s*=|normalBias")
# A light this file creates — only its creator owns the shadow bias.
RE_THREE_LIGHT_CREATION = re.compile(
    r"new\s+(?:THREE\.)?(DirectionalLight|PointLight|SpotLight|HemisphereLight"
    r"|RectAreaLight|SunLight)\s*\("
)
RE_THREE_RENDERER = re.compile(r"new\s+(?:THREE\.)?WebGLRenderer\s*\(")
RE_THREE_OUTPUT_COLOR_SPACE = re.compile(r"outputColorSpace")
# Only an *instantiated* loader matters. GLTFExporter and friends share the
# substring "GLTF" but never fetch a compressed payload.
RE_THREE_GLTF_LOADER = re.compile(r"new\s+(?:THREE\.)?GLTFLoader\s*\(")
RE_THREE_DECODERS = re.compile(r"DRACOLoader|MeshoptDecoder|KTX2Loader")
RE_THREE_RESIZE = re.compile(
    r"addEventListener\s*\(\s*['\"]resize['\"]|ResizeObserver|\.setSize\s*\("
)
# A file is treated as three.js code only if it actually references the library
RE_THREE_PROJECT = re.compile(
    r"from\s+['\"]three(?:/[^'\"]*)?['\"]|require\s*\(\s*['\"]three['\"]\s*\)"
    r"|\bTHREE\.",
    re.IGNORECASE,
)

# --- Scope analysis (so a rule can tell module scope from a frame callback) ---
RE_CONSTRUCTOR = re.compile(r"\bconstructor\s*\(")
RE_STRING_OR_COMMENT = re.compile(
    r"//.*$|/\*.*?\*/|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`",
    re.DOTALL,
)
# Identifiers that open a control-flow block, not a function body.
BLOCK_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "do", "try", "finally", "else",
    "return", "typeof", "new", "delete", "void", "await", "yield", "case",
    "default", "in", "of", "super", "this", "with", "enum", "const", "let",
    "var", "function", "import", "export",
}
RE_METHOD_HEADER = re.compile(r"([A-Za-z_$][\w$]*)\s*\([^()]*\)\s*$")
RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
RE_LINE_COMMENT = re.compile(r"//.*$")


def blank_block_comments(text: str) -> str:
    """Remove /* ... */ blocks while PRESERVING line numbers.

    A multi-line JSDoc example containing `castShadow = true` is documentation,
    not code, and must not trip a rule.
    """
    return RE_BLOCK_COMMENT.sub(
        lambda m: "\n" * m.group(0).count("\n"), text
    )


JS_EXTS = {".js", ".jsx", ".ts", ".tsx"}



EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    ".svelte-kit",
    "__pycache__",
    ".pytest_cache",
    "coverage",
}

# Keep in sync with SKILL.md `version:` — the linter advertises it.
LINTER_VERSION = "1.3.0"

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

# ---------------------------------------------------------------------------
# Scanner Engine
# ---------------------------------------------------------------------------

class VisualAuditor:
    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.files_scanned = 0
        self.total_loc = 0
        self.unreadable = 0
        self.defects: List[Dict[str, Any]] = []
        self.has_reduced_motion = False
        self.has_motion = False

    def scan(self) -> Dict[str, Any]:
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in {".css", ".scss", ".sass", ".less", ".html", ".js", ".jsx", ".ts", ".tsx", ".svelte", ".vue", ".py", ".gd"}:
                    full_path = os.path.join(root, file)
                    self._scan_file(full_path, ext)

        # Cross-file check: ANY declared transition/animation without a
        # reduced-motion guard is a failure — gating this on layout-thrashing
        # defects missed the common case (transform/opacity-only animation).
        if self.files_scanned > 0 and self.has_motion and not self.has_reduced_motion:
            self.defects.append({
                "file": "Global Stylesheet / Media Queries",
                "line": 1,
                "code": "MISSING_REDUCED_MOTION_GUARD",
                "severity": "HIGH",
                "message": "Animations or transitions detected across project but zero @media (prefers-reduced-motion) declarations found.",
                "fix": "Add @media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; } .btn-spinner { animation-duration: 1.5s !important; } }"
            })

        # Calculate weighted score
        penalty = sum(SEVERITY_WEIGHTS.get(d["severity"], 2) for d in self.defects)
        score = max(0, 100 - penalty)

        # Sort defects by severity (HIGH first, then MEDIUM, then LOW)
        sorted_defects = sorted(self.defects, key=lambda d: SEVERITY_ORDER.get(d["severity"], 99))

        return {
            "target_dir": self.root_dir,
            "files_scanned": self.files_scanned,
            "unreadable_files": self.unreadable,
            "total_loc": self.total_loc,
            "visual_health_score": score,
            "defects_count": len(self.defects),
            "defects": sorted_defects,
        }

    def _scan_file(self, path: str, ext: str):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError as exc:
            # Count it: a run that could not read files must not report a clean
            # bill of health.
            self.unreadable += 1
            self.defects.append({
                "file": os.path.relpath(path, self.root_dir),
                "line": 0,
                "code": "UNREADABLE_SOURCE",
                "severity": "MEDIUM",
                "message": f"Could not read file: {exc}",
                "fix": "Fix file permissions or exclude the path explicitly.",
            })
            return

        self.files_scanned += 1
        lines = content.splitlines()
        self.total_loc += len(lines)
        rel_path = os.path.relpath(path, self.root_dir)

        if "prefers-reduced-motion" in content:
            self.has_reduced_motion = True
        if re.search(r"\b(?:transition|animation)\s*:", content, re.IGNORECASE):
            self.has_motion = True

        # Three.js context: only JS/TS-family files that actually reference three.
        is_three = ext in JS_EXTS and bool(RE_THREE_PROJECT.search(content))
        has_render_loop = bool(RE_THREE_RENDER_LOOP.search(content))
        # Comment-free view of the file: comments are documentation, and braces
        # inside them would corrupt the scope map.
        code_lines = [RE_STRING_OR_COMMENT.sub("", l) for l in blank_block_comments(content).splitlines()]
        # Scope map lets the rules tell module scope from a per-frame callback.
        scope_map = self._scope_map(code_lines) if is_three else []

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            # Ignore comments
            if stripped.startswith(("#", "//", "/*", "*")):
                continue

            # 1. Layout Thrashing in CSS / Transitions
            m_layout = RE_LAYOUT_ANIM.search(line)
            if m_layout:
                self.defects.append({
                    "file": rel_path,
                    "line": idx,
                    "code": "LAYOUT_THRASHING_ANIMATION",
                    "severity": "HIGH",
                    "message": f"Transition/animation triggers layout reflow: '{m_layout.group(0).strip()}'.",
                    "fix": "Animate compositor-only properties ('transform', 'opacity') using CSS scale/translate or matrix3d."
                })

            # 2. Large or un-budgeted backdrop blurs
            m_blur = RE_BACKDROP_BLUR.search(line)
            if m_blur:
                radius_str = m_blur.group(1).strip()
                px_match = re.search(r"(\d+)\s*px", radius_str)
                if px_match and int(px_match.group(1)) > 16:
                    self.defects.append({
                        "file": rel_path,
                        "line": idx,
                        "code": "EXCESSIVE_BLUR_OVERDRAW",
                        "severity": "MEDIUM",
                        "message": f"backdrop-filter blur radius ({px_match.group(1)}px) exceeds safe 16px frame budget.",
                        "fix": "Clamp blur radius <= 16px and ensure maximum 2 overlapping blur layers."
                    })

            # 3. Fixed per-frame lerping in JS / TS / Game scripts
            m_lerp = RE_FIXED_LERP_ASSIGN.search(line) or RE_FIXED_LERP_FN.search(line)
            if m_lerp and ext in {".js", ".ts", ".jsx", ".tsx", ".py", ".gd"}:
                self.defects.append({
                    "file": rel_path,
                    "line": idx,
                    "code": "FRAME_RATE_DEPENDENT_LERP",
                    "severity": "HIGH",
                    "message": f"Fixed multiplier animation loop '{m_lerp.group(0)}' runs at variable speeds on 60Hz vs 120Hz.",
                    "fix": "Use delta-time exponential decay: expDecay(current, target, decay, dt) or stepSpringSubstepped()."
                })

            # 4. Telemetry / Metric naming without tabular numbers
            if ext in {".html", ".jsx", ".tsx", ".svelte", ".vue"} and RE_DYNAMIC_METRIC.search(line):
                if not RE_TABULAR_NUMS.search(line):
                    # Flag if nearby context doesn't indicate tabular-nums
                    snippet = "\n".join(lines[max(0, idx - 5):min(len(lines), idx + 5)])
                    if not RE_TABULAR_NUMS.search(snippet):
                        self.defects.append({
                            "file": rel_path,
                            "line": idx,
                            "code": "NUMERIC_JITTER_HAZARD",
                            "severity": "LOW",
                            "message": f"Dynamic counter/metric readout element may lack tabular-nums: '{line.strip()[:60]}'.",
                            "fix": "Apply font-variant-numeric: tabular-nums; to prevent horizontal number oscillation."
                        })

            # 5. Three.js: unclamped device pixel ratio (fill-rate collapse on 3x phones)
            if is_three and RE_SET_PIXEL_RATIO.search(line):
                m_pr = RE_SET_PIXEL_RATIO.search(line)
                arg = m_pr.group(1) if m_pr else ""
                if RE_PIXEL_RATIO_UNCLAMPED.search(arg) and not RE_PIXEL_RATIO_CLAMPED.search(arg):
                    self.defects.append({
                        "file": rel_path,
                        "line": idx,
                        "code": "THREE_UNCLAMPED_PIXEL_RATIO",
                        "severity": "HIGH",
                        "message": f"setPixelRatio() uses the raw devicePixelRatio without a clamp: '{line.strip()[:70]}'.",
                        "fix": "Clamp the buffer scale: renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))."
                    })

            # 6. Three.js: zero-argument scratch allocation inside a render-loop file
            if is_three and has_render_loop and RE_THREE_SCRATCH_ALLOC.search(code_lines[idx - 1]):
                enclosing, _innermost = scope_map[idx - 1]
                # Module-scope scratch objects are the idiomatic three.js pattern
                # (allocated once, reused every frame) — never flag them.
                # Class fields allocate once per instance, not per frame.
                # Constructor bodies allocate once.
                in_function = any(k in ("func", "ctor") for k in enclosing)
                in_ctor = "ctor" in enclosing
                if not in_function or in_ctor:
                    continue
                self.defects.append({
                    "file": rel_path,
                    "line": idx,
                    "code": "THREE_PER_FRAME_ALLOCATION",
                    "severity": "MEDIUM",
                    "message": f"Scratch object allocated with no arguments inside a function: '{code_lines[idx - 1].strip()[:70]}'. In a per-frame callback this is GC pressure.",
                    "fix": "Hoist reusable scratch vectors/quaternions to module scope and mutate them in place (v.copy(...), q.setFromEuler(...))."
                })

        # ---- Three.js file-level checks (need whole-file context) ----
        if is_three:
            self._scan_three_file(rel_path, code_lines)

    @staticmethod
    def _classify_block(header: str) -> str:
        """Classify the block a header opens: 'class' | 'ctor' | 'func' | 'block'."""
        h = header.strip()
        if not h:
            return "block"
        if re.search(r"\bclass\b", h):
            return "class"
        if RE_CONSTRUCTOR.search(h):
            return "ctor"
        if re.search(r"\bfunction\b", h) or "=>" in h:
            return "func"
        # Method shorthand: `render() {`, `obj.update() {`, `get size() {`
        m = RE_METHOD_HEADER.search(h)
        if m and m.group(1) not in BLOCK_KEYWORDS:
            return "func"
        return "block"

    @staticmethod
    def _scope_map(lines: List[str]):
        """Return [(stack_snapshot, innermost_kind)] per line.

        stack_snapshot is the list of enclosing block kinds at the START of the
        line ('class', 'ctor', 'func', 'block'). innermost_kind is the kind of
        the innermost enclosing block, or None at module scope.

        Brace matching is parenthesis-aware: a destructuring parameter list
        such as `constructor( capacity, { shadow } ) {` opens TWO braces, and
        only the paren-depth-0 one is the constructor body.
        """
        stack: List[str] = []
        out: List[tuple] = []
        for line in lines:
            code = RE_STRING_OR_COMMENT.sub("", line)

            # Pass 1 — locate the block-opening brace (first '{' at paren depth 0)
            # and the header that precedes it.
            idx_brace = -1
            paren = 0
            for i, ch in enumerate(code):
                if ch in "([":
                    paren += 1
                elif ch in ")]":
                    paren -= 1
                elif ch == "{" and paren == 0:
                    idx_brace = i
                    break
            header = code[:idx_brace] if idx_brace >= 0 else code
            kind = VisualAuditor._classify_block(header)

            out.append((list(stack), stack[-1] if stack else None))

            # Pass 2 — push/pop every brace, tagging the body brace with `kind`
            paren = 0
            body_pushed = False
            for ch in code:
                if ch in "([":
                    paren += 1
                elif ch in ")]":
                    paren -= 1
                elif ch == "{":
                    if paren == 0 and not body_pushed:
                        stack.append(kind)
                        body_pushed = True
                    else:
                        stack.append("block")
                elif ch == "}":
                    if stack:
                        stack.pop()
        return out

    def _scan_three_file(self, rel_path: str, code_lines: List[str]):
        """Three.js hazards that can only be judged with whole-file context.

        `code_lines` is already stripped of comments and string literals.
        """
        code = "\n".join(code_lines)

        # 5a. A renderer created and never disposed — the renderer is unambiguously
        # owned by the file that constructs it.
        if RE_THREE_RENDERER.search(code) and not RE_THREE_DISPOSE.search(code):
            for idx, line in enumerate(code_lines, 1):
                if RE_THREE_RENDERER.search(line):
                    self.defects.append({
                        "file": rel_path,
                        "line": idx,
                        "code": "THREE_MISSING_DISPOSE",
                        "severity": "MEDIUM",
                        "message": "A WebGLRenderer is created here but the file never calls .dispose() — the WebGL context and its GPU resources leak on teardown.",
                        "fix": "Call renderer.dispose() (and renderer.forceContextLoss() in dev) when the owning view unmounts."
                    })
                    break

        # 5b. Shadows enabled on a light this file creates, without bias tuning.
        # Only the file that CREATES the light owns its bias — a loader that sets
        # castShadow on imported meshes does not.
        if (RE_THREE_LIGHT_CREATION.search(code)
                and RE_THREE_CAST_SHADOW.search(code)
                and not RE_THREE_SHADOW_BIAS.search(code)):
            for idx, line in enumerate(code_lines, 1):
                if RE_THREE_CAST_SHADOW.search(line):
                    self.defects.append({
                        "file": rel_path,
                        "line": idx,
                        "code": "THREE_MISSING_SHADOW_BIAS",
                        "severity": "MEDIUM",
                        "message": "This file creates a light and enables castShadow but sets no shadow.bias / shadow.normalBias — shadow acne and peter-panning are likely.",
                        "fix": "Tune the light: light.shadow.bias = -0.0004 and light.shadow.normalBias = 0.02 (scale normalBias to your world units)."
                    })
                    break

        # 5c. Renderer without an explicit output colour space
        if RE_THREE_RENDERER.search(code) and not RE_THREE_OUTPUT_COLOR_SPACE.search(code):
            for idx, line in enumerate(code_lines, 1):
                if RE_THREE_RENDERER.search(line):
                    self.defects.append({
                        "file": rel_path,
                        "line": idx,
                        "code": "THREE_UNSET_OUTPUT_COLOR_SPACE",
                        "severity": "LOW",
                        "message": "WebGLRenderer created without an explicit outputColorSpace setting.",
                        "fix": "Set renderer.outputColorSpace = THREE.SRGBColorSpace explicitly (default since r152, but pinning it prevents silent regressions)."
                    })
                    break

        # 5d. An instantiated GLTFLoader with no Draco / meshopt / KTX2 decoder.
        if RE_THREE_GLTF_LOADER.search(code) and not RE_THREE_DECODERS.search(code):
            for idx, line in enumerate(code_lines, 1):
                if RE_THREE_GLTF_LOADER.search(line):
                    self.defects.append({
                        "file": rel_path,
                        "line": idx,
                        "code": "THREE_UNCOMPRESSED_GLTF",
                        "severity": "LOW",
                        "message": "GLTFLoader is instantiated with no Draco / meshopt / KTX2 decoder — payloads stay 3-10x larger than necessary.",
                        "fix": "Wire decoders: loader.setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder) and ktx2.detectSupport(renderer)."
                    })
                    break

        # 5e. Renderer without resize handling
        if RE_THREE_RENDERER.search(code) and not RE_THREE_RESIZE.search(code):
            for idx, line in enumerate(code_lines, 1):
                if RE_THREE_RENDERER.search(line):
                    self.defects.append({
                        "file": rel_path,
                        "line": idx,
                        "code": "THREE_MISSING_RESIZE_HANDLER",
                        "severity": "LOW",
                        "message": "WebGLRenderer created with no resize listener or ResizeObserver.",
                        "fix": "Handle resize: update camera.aspect + camera.updateProjectionMatrix() and renderer.setSize(w, h, false)."
                    })
                    break

# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Zero-mutation UI/GUI visual linter.")
    parser.add_argument("target_dir", nargs="?", default=".", help="Target repository or UI directory")
    parser.add_argument("--out", help="Write JSON audit report to file")
    parser.add_argument(
        "--fail-on",
        choices=["high", "medium", "low"],
        default=None,
        help="Exit 1 when a defect at or above this severity is present (CI gate).",
    )
    args = parser.parse_args()

    auditor = VisualAuditor(args.target_dir)
    results = auditor.scan()

    print(f"\n========================================================")
    print(f" Plastic Surgery Preflight Visual Linter (v{LINTER_VERSION})")
    print(f" Target: {results['target_dir']}")
    print(f" Files Scanned: {results['files_scanned']} | Total LOC: {results['total_loc']}")
    if results["unreadable_files"]:
        print(f" Unreadable Files: {results['unreadable_files']} (counted as MEDIUM defects)")
    print(f" Visual Health Score: {results['visual_health_score']} / 100")
    print(f" Detected Defects: {results['defects_count']}")
    print(f"========================================================\n")

    if results["defects"]:
        # Defects are pre-sorted by severity: HIGH first, then MEDIUM, then LOW
        for d in results["defects"][:20]:
            print(f"[{d['severity']}] {d['code']} at {d['file']}:{d['line']}")
            print(f"  Issue: {d['message']}")
            print(f"  Fix:   {d['fix']}\n")
        if len(results["defects"]) > 20:
            print(f"... and {len(results['defects']) - 20} more defects (see --out report.json)")
    else:
        print("✓ Zero visual or compositor defects detected. Clean presentation skin!")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nReport saved to: {args.out}")

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on.upper()]
        worst = min((SEVERITY_ORDER[d["severity"]] for d in results["defects"]), default=99)
        if worst <= threshold:
            print(f"GATE FAILED: defect at or above {args.fail_on.upper()} present.")
            return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
