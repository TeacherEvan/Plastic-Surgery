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


class ThreeJsRules(unittest.TestCase):
    """The 3D rules must fire on real three.js code and stay silent elsewhere."""

    def _scan(self, files: dict[str, str]):
        with tempfile.TemporaryDirectory() as td:
            for name, body in files.items():
                p = Path(td) / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            return VisualAuditor(td).scan()

    def _codes(self, files: dict[str, str]):
        return [d["code"] for d in self._scan(files)["defects"]]

    def test_unclamped_pixel_ratio_is_high(self):
        r = self._scan({"a.ts": (
            "import * as THREE from 'three';\n"
            "const renderer = new THREE.WebGLRenderer();\n"
            "renderer.setPixelRatio(window.devicePixelRatio);\n"
        )})
        sev = {d["code"]: d["severity"] for d in r["defects"]}
        self.assertIn("THREE_UNCLAMPED_PIXEL_RATIO", sev)
        self.assertEqual(sev["THREE_UNCLAMPED_PIXEL_RATIO"], "HIGH")

    def test_clamped_pixel_ratio_is_clean(self):
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "const renderer = new THREE.WebGLRenderer();\n"
            "renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));\n"
        )})
        self.assertNotIn("THREE_UNCLAMPED_PIXEL_RATIO", codes)

    def test_per_frame_allocation_is_medium(self):
        r = self._scan({"a.ts": (
            "import * as THREE from 'three';\n"
            "function frame() {\n"
            "  const v = new THREE.Vector3();\n"
            "  requestAnimationFrame(frame);\n"
            "}\n"
        )})
        sev = {d["code"]: d["severity"] for d in r["defects"]}
        self.assertIn("THREE_PER_FRAME_ALLOCATION", sev)
        self.assertEqual(sev["THREE_PER_FRAME_ALLOCATION"], "MEDIUM")

    def test_missing_dispose_is_flagged(self):
        # The renderer is unambiguously owned by the file that constructs it.
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "const renderer = new THREE.WebGLRenderer();\n"
        )})
        self.assertIn("THREE_MISSING_DISPOSE", codes)

    def test_dispose_present_satisfies_check(self):
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "const renderer = new THREE.WebGLRenderer();\n"
            "function teardown() { renderer.dispose(); }\n"
        )})
        self.assertNotIn("THREE_MISSING_DISPOSE", codes)

    def test_passing_geometry_to_another_owner_is_not_a_dispose_defect(self):
        # A file that merely constructs a geometry does not own its teardown.
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "export function makeGeo() { return new THREE.BufferGeometry(); }\n"
        )})
        self.assertNotIn("THREE_MISSING_DISPOSE", codes)

    def test_module_scope_scratch_is_not_flagged(self):
        # Module-scope scratch objects are the idiomatic three.js pattern:
        # allocated once, reused every frame. Never a per-frame allocation.
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "const _v = new THREE.Vector3();\n"
            "function frame() { requestAnimationFrame(frame); }\n"
        )})
        self.assertNotIn("THREE_PER_FRAME_ALLOCATION", codes)

    def test_constructor_scratch_is_not_flagged(self):
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "class Pipeline {\n"
            "  constructor() {\n"
            "    this.v = new THREE.Vector3();\n"
            "  }\n"
            "  render() { requestAnimationFrame(() => this.render()); }\n"
            "}\n"
        )})
        self.assertNotIn("THREE_PER_FRAME_ALLOCATION", codes)

    def test_shadow_bias_only_fires_for_light_creators(self):
        # A loader that flags imported meshes as castShadow does not own the
        # application's shadow bias.
        loader_codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "mesh.castShadow = true;\n"
        )})
        self.assertNotIn("THREE_MISSING_SHADOW_BIAS", loader_codes)

        light_codes = self._codes({"b.ts": (
            "import * as THREE from 'three';\n"
            "const sun = new THREE.DirectionalLight(0xffffff, 2.5);\n"
            "sun.castShadow = true;\n"
        )})
        self.assertIn("THREE_MISSING_SHADOW_BIAS", light_codes)

    def test_gltf_exporter_is_not_flagged(self):
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';\n"
            "const exporter = new GLTFExporter();\n"
        )})
        self.assertNotIn("THREE_UNCOMPRESSED_GLTF", codes)

    def test_jsdoc_example_is_not_code(self):
        """A `castShadow = true` inside a multi-line JSDoc block is documentation."""
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "/**\n"
            " * ```js\n"
            " * const sun = new THREE.DirectionalLight();\n"
            " * sun.castShadow = true;\n"
            " * ```\n"
            " */\n"
            "export const x = 1;\n"
        )})
        self.assertNotIn("THREE_MISSING_SHADOW_BIAS", codes)

    def test_destructuring_constructor_is_recognised(self):
        """`constructor( cap, { shadow } ) {` opens two braces; only the body counts."""
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "class Pipeline {\n"
            "  constructor( cap, { shadow } ) {\n"
            "    this.v = new THREE.Vector3();\n"
            "  }\n"
            "  render() { requestAnimationFrame(() => this.render()); }\n"
            "}\n"
        )})
        self.assertNotIn("THREE_PER_FRAME_ALLOCATION", codes)

    def test_gltf_without_decoders_is_flagged(self):
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';\n"
            "const loader = new GLTFLoader();\n"
        )})
        self.assertIn("THREE_UNCOMPRESSED_GLTF", codes)

    def test_gltf_with_draco_is_clean(self):
        codes = self._codes({"a.ts": (
            "import * as THREE from 'three';\n"
            "import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';\n"
            "const loader = new GLTFLoader().setDRACOLoader(draco);\n"
        )})
        self.assertNotIn("THREE_UNCOMPRESSED_GLTF", codes)

    def test_non_three_files_are_not_scanned_for_3d_rules(self):
        # No three.js reference at all -> the 3D rules must not fire, even when the
        # same-looking allocation / renderer calls appear.
        codes = self._codes({"a.ts": (
            "const v = new Vector3();\n"
            "const renderer = new WebGLRenderer();\n"
            "renderer.setPixelRatio(window.devicePixelRatio);\n"
        )})
        self.assertEqual([c for c in codes if c.startswith("THREE_")], [])

    def test_three_reference_without_import_is_still_scanned(self):
        # THREE used as a global (no import statement) is still three.js code.
        codes = self._codes({"a.ts": (
            "const renderer = new THREE.WebGLRenderer();\n"
            "renderer.setPixelRatio(window.devicePixelRatio);\n"
        )})
        self.assertIn("THREE_UNCLAMPED_PIXEL_RATIO", codes)

    def test_python_and_css_files_never_trigger_3d_rules(self):
        codes = self._codes({
            "a.py": "import THREE\nx = new THREE.Vector3()\n",
            "a.css": ".x{color:red}\n",
        })
        self.assertEqual([c for c in codes if c.startswith("THREE_")], [])


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
