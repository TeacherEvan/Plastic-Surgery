"""Behavioural tests for preflight_visual_lint.py.

Run: python3 -m unittest discover -s tests -v
No third-party dependencies (the linter itself is stdlib-only).
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "scripts" / "preflight_visual_lint.py"

sys.path.insert(0, str(ROOT / "scripts"))
from preflight_visual_lint import VisualAuditor  # noqa: E402


class AuditorBehaviour(unittest.TestCase):
    def _scan(self, files: dict[str, str]):
        with tempfile.TemporaryDirectory() as td:
            for name, body in files.items():
                p = Path(td) / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            return VisualAuditor(td).scan()

    def test_layout_thrashing_transition_is_high(self):
        r = self._scan({"a.css": ".x{transition: width .2s ease}\n"})
        codes = [d["code"] for d in r["defects"]]
        self.assertIn("LAYOUT_THRASHING_ANIMATION", codes)
        sev = {d["code"]: d["severity"] for d in r["defects"]}
        self.assertEqual(sev["LAYOUT_THRASHING_ANIMATION"], "HIGH")

    def test_missing_reduced_motion_flagged_for_transform_only_motion(self):
        # Regression: the guard used to require a layout-thrashing defect.
        r = self._scan({"a.css": ".x{transition: transform .2s ease}\n"})
        codes = [d["code"] for d in r["defects"]]
        self.assertIn("MISSING_REDUCED_MOTION_GUARD", codes)

    def test_reduced_motion_guard_satisfies_the_check(self):
        r = self._scan({
            "a.css": ".x{transition: transform .2s ease}\n"
                     "@media (prefers-reduced-motion: reduce){.x{transition:none}}\n"
        })
        codes = [d["code"] for d in r["defects"]]
        self.assertNotIn("MISSING_REDUCED_MOTION_GUARD", codes)

    def test_clean_project_scores_100(self):
        r = self._scan({"a.css": ".x{color:red}\n"})
        self.assertEqual(r["defects_count"], 0)
        self.assertEqual(r["visual_health_score"], 100)

    def test_oversized_blur_is_medium(self):
        r = self._scan({"a.css": ".x{backdrop-filter: blur(32px)}\n"})
        sev = {d["code"]: d["severity"] for d in r["defects"]}
        self.assertEqual(sev.get("EXCESSIVE_BLUR_OVERDRAW"), "MEDIUM")

    def test_fixed_lerp_is_high(self):
        r = self._scan({"a.ts": "this.x += (target - this.x) * 0.1;\n"})
        codes = [d["code"] for d in r["defects"]]
        self.assertIn("FRAME_RATE_DEPENDENT_LERP", codes)

    @unittest.skipIf(hasattr(__import__("os"), "geteuid") and __import__("os").geteuid() == 0,
                     "root can read anything")
    def test_unreadable_file_is_counted_not_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "secret.css"
            p.write_text(".x{color:red}", encoding="utf-8")
            p.chmod(0o000)
            try:
                r = VisualAuditor(td).scan()
            finally:
                p.chmod(0o644)
            self.assertEqual(r["unreadable_files"], 1)
            self.assertIn("UNREADABLE_SOURCE", [d["code"] for d in r["defects"]])


class CliGate(unittest.TestCase):
    def _run(self, files: dict[str, str], *args: str):
        with tempfile.TemporaryDirectory() as td:
            for name, body in files.items():
                (Path(td) / name).write_text(body, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(LINTER), td, *args],
                capture_output=True, text=True, check=False,
            )

    def test_exit_zero_without_fail_on_even_with_defects(self):
        r = self._run({"a.css": ".x{transition: width .2s}\n"})
        self.assertEqual(r.returncode, 0)

    def test_fail_on_high_exits_one(self):
        r = self._run({"a.css": ".x{transition: width .2s}\n"}, "--fail-on", "high")
        self.assertEqual(r.returncode, 1)
        self.assertIn("GATE FAILED", r.stdout)

    def test_fail_on_high_exits_zero_when_clean(self):
        r = self._run({"a.css": ".x{color:red}\n"}, "--fail-on", "high")
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
