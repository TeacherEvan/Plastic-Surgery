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
        self.defects: List[Dict[str, Any]] = []
        self.has_reduced_motion = False
        self.has_tabular_nums = False

    def scan(self) -> Dict[str, Any]:
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in {".css", ".scss", ".sass", ".less", ".html", ".js", ".jsx", ".ts", ".tsx", ".svelte", ".vue", ".py", ".gd"}:
                    full_path = os.path.join(root, file)
                    self._scan_file(full_path, ext)

        # Cross-file check: if animations are present but no prefers-reduced-motion exists
        if self.files_scanned > 0 and not self.has_reduced_motion and any(d["code"] == "LAYOUT_THRASHING_ANIMATION" for d in self.defects):
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
            "total_loc": self.total_loc,
            "visual_health_score": score,
            "defects_count": len(self.defects),
            "defects": sorted_defects,
        }

    def _scan_file(self, path: str, ext: str):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return

        self.files_scanned += 1
        lines = content.splitlines()
        self.total_loc += len(lines)
        rel_path = os.path.relpath(path, self.root_dir)

        if "prefers-reduced-motion" in content:
            self.has_reduced_motion = True
        if RE_TABULAR_NUMS.search(content):
            self.has_tabular_nums = True

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

# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Zero-mutation UI/GUI visual linter.")
    parser.add_argument("target_dir", nargs="?", default=".", help="Target repository or UI directory")
    parser.add_argument("--out", help="Write JSON audit report to file")
    args = parser.parse_args()

    auditor = VisualAuditor(args.target_dir)
    results = auditor.scan()

    print(f"\n========================================================")
    print(f" Plastic Surgery Preflight Visual Linter (v1.1.0)")
    print(f" Target: {results['target_dir']}")
    print(f" Files Scanned: {results['files_scanned']} | Total LOC: {results['total_loc']}")
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

if __name__ == "__main__":
    main()
