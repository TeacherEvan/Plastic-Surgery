"""Behavioural tests for preflight_visual_lint.py.

Run: pytest -v tests/test_visual_lint.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "scripts" / "preflight_visual_lint.py"
SCHEMA_PATH = ROOT / "schemas" / "visual-lint-report.schema.json"

sys.path.insert(0, str(ROOT / "scripts"))
from preflight_visual_lint import VisualAuditor, build_sarif  # noqa: E402


class AuditorBehaviour(unittest.TestCase):
    def _scan(self, files: dict[str, str]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            for name, body in files.items():
                p = Path(td) / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            result: dict[str, Any] = VisualAuditor(td).scan()
            return result

    def test_layout_thrashing_transition_is_high(self) -> None:
        r = self._scan({"a.css": ".x{transition: width .2s ease}\n"})
        codes = [d["code"] for d in r["defects"]]
        self.assertIn("LAYOUT_THRASHING_ANIMATION", codes)
        sev = {d["code"]: d["severity"] for d in r["defects"]}
        self.assertEqual(sev["LAYOUT_THRASHING_ANIMATION"], "HIGH")

    def test_transition_property_and_keyframes_trigger_layout_thrash(self) -> None:
        r = self._scan(
            {
                "a.css": (
                    ".card { transition-property: width; }\n"
                    "@keyframes expand { from { height: 0; } to { height: 100px; } }\n"
                )
            }
        )
        codes = [d["code"] for d in r["defects"]]
        self.assertEqual(codes.count("LAYOUT_THRASHING_ANIMATION"), 2)

    def test_keyframe_name_slide_left_does_not_false_positive(self) -> None:
        r = self._scan(
            {
                "a.css": (
                    "@keyframes slide-left { to { transform: translateX(0); } }\n"
                    "@media (prefers-reduced-motion: reduce) { * { animation: none; } }\n"
                    "@media (prefers-contrast: more) { :root { --c: 1; } }\n"
                )
            }
        )
        codes = [d["code"] for d in r["defects"]]
        self.assertNotIn("LAYOUT_THRASHING_ANIMATION", codes)

    def test_missing_reduced_motion_flagged_for_transform_only_motion(self) -> None:
        r = self._scan({"a.css": ".x{transition: transform .2s ease}\n"})
        codes = [d["code"] for d in r["defects"]]
        self.assertIn("MISSING_REDUCED_MOTION_GUARD", codes)

    def test_reduced_motion_and_contrast_guards_satisfy_checks(self) -> None:
        r = self._scan(
            {
                "a.css": (
                    ".x{transition: transform .2s ease}\n"
                    "@media (prefers-reduced-motion: reduce){.x{transition:none}}\n"
                    "@media (prefers-contrast: more){.x{border-width:2px}}\n"
                    "@media (forced-colors: active){.x{border:1px solid ButtonText}}\n"
                )
            }
        )
        codes = [d["code"] for d in r["defects"]]
        self.assertNotIn("MISSING_REDUCED_MOTION_GUARD", codes)
        self.assertNotIn("WCAG_MISSING_CONTRAST_OR_FORCED_COLORS", codes)

    def test_wcag_missing_contrast_or_forced_colors_flagged(self) -> None:
        r = self._scan(
            {
                "a.css": (
                    ".x{transition: transform .2s ease}\n"
                    "@media (prefers-reduced-motion: reduce){.x{transition:none}}\n"
                )
            }
        )
        codes = [d["code"] for d in r["defects"]]
        self.assertIn("WCAG_MISSING_CONTRAST_OR_FORCED_COLORS", codes)

    def test_wcag_small_target_size_detected_and_larger_target_passes(self) -> None:
        r_bad = self._scan(
            {
                "a.css": ".icon-btn { width: 18px; height: 18px; }\n",
                "b.tsx": "export const B = () => <button style={{ width: 20, height: 20 }}>X</button>;\n",
            }
        )
        bad_codes = [d["code"] for d in r_bad["defects"]]
        self.assertGreaterEqual(bad_codes.count("WCAG_SMALL_TARGET_SIZE"), 2)

        r_ok = self._scan(
            {
                "a.css": ".icon-btn { width: 28px; height: 28px; }\n",
                "b.tsx": "export const B = () => <button style={{ width: 32, height: 32 }}>X</button>;\n",
            }
        )
        ok_codes = [d["code"] for d in r_ok["defects"]]
        self.assertNotIn("WCAG_SMALL_TARGET_SIZE", ok_codes)

    def test_wcag_sticky_focus_obscured_and_scroll_margin_satisfier(self) -> None:
        r_bad = self._scan(
            {".css".replace(".", "a."): ".site-header { position: sticky; top: 0; }\n"}
        )
        self.assertIn(
            "WCAG_STICKY_FOCUS_OBSCURED", [d["code"] for d in r_bad["defects"]]
        )

        r_ok = self._scan(
            {
                "a.css": (
                    ".site-header { position: sticky; top: 0; }\n"
                    ":target { scroll-margin-top: 64px; }\n"
                )
            }
        )
        self.assertNotIn(
            "WCAG_STICKY_FOCUS_OBSCURED", [d["code"] for d in r_ok["defects"]]
        )

    def test_text_wrap_balance_is_not_flagged_as_numeric_jitter(self) -> None:
        r_clean = self._scan(
            {
                "a.tsx": (
                    "export const Hero = () => (\n"
                    "  <h1 style={{ textWrap: 'balance' }} className='text-wrap: balance'>Title</h1>\n"
                    ");\n"
                )
            }
        )
        codes_clean = [d["code"] for d in r_clean["defects"]]
        self.assertNotIn("NUMERIC_JITTER_HAZARD", codes_clean)

        r_real = self._scan(
            {"b.tsx": "export const Stat = () => <span>{account.balance}</span>;\n"}
        )
        codes_real = [d["code"] for d in r_real["defects"]]
        self.assertIn("NUMERIC_JITTER_HAZARD", codes_real)

    def test_clean_project_scores_100(self) -> None:
        r = self._scan({"a.css": ".x{color:red}\n"})
        self.assertEqual(r["defects_count"], 0)
        self.assertEqual(r["visual_health_score"], 100)

    def test_oversized_blur_is_medium(self) -> None:
        r = self._scan({"a.css": ".x{backdrop-filter: blur(32px)}\n"})
        sev = {d["code"]: d["severity"] for d in r["defects"]}
        self.assertEqual(sev.get("EXCESSIVE_BLUR_OVERDRAW"), "MEDIUM")

    def test_fixed_lerp_and_two_arg_three_lerp_slerp_are_high(self) -> None:
        r = self._scan(
            {
                "a.ts": (
                    "this.x += (target - this.x) * 0.1;\n"
                    "pos.lerp(target, 0.1);\n"
                    "quat.slerp(targetQ, 0.15);\n"
                )
            }
        )
        codes = [d["code"] for d in r["defects"]]
        self.assertEqual(codes.count("FRAME_RATE_DEPENDENT_LERP"), 3)

    def test_excluded_build_dirs_are_skipped(self) -> None:
        r = self._scan(
            {
                "playwright-report/trace.css": ".bad{transition:width .2s}\n",
                "test-results/out.css": ".bad{transition:height .2s}\n",
                "venv/style.css": ".bad{backdrop-filter:blur(40px)}\n",
                "src/ok.css": ".ok{color:red}\n",
            }
        )
        self.assertEqual(r["files_scanned"], 1)
        self.assertEqual(r["defects_count"], 0)

    @unittest.skipIf(
        hasattr(os, "geteuid") and os.geteuid() == 0,
        "root can read anything",
    )
    def test_unreadable_file_is_counted_not_ignored(self) -> None:
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
    """Ensure 3D rules fire on real three.js code and stay silent elsewhere."""

    def _scan(self, files: dict[str, str]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            for name, body in files.items():
                p = Path(td) / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            result: dict[str, Any] = VisualAuditor(td).scan()
            return result

    def _codes(self, files: dict[str, str]) -> list[str]:
        return [str(d["code"]) for d in self._scan(files)["defects"]]

    def test_unclamped_pixel_ratio_is_high(self) -> None:
        r = self._scan(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "const renderer = new THREE.WebGLRenderer();\n"
                    "renderer.setPixelRatio(window.devicePixelRatio);\n"
                )
            }
        )
        sev = {d["code"]: d["severity"] for d in r["defects"]}
        self.assertIn("THREE_UNCLAMPED_PIXEL_RATIO", sev)
        self.assertEqual(sev["THREE_UNCLAMPED_PIXEL_RATIO"], "HIGH")

    def test_clamped_pixel_ratio_is_clean(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "const renderer = new THREE.WebGLRenderer();\n"
                    "renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));\n"
                )
            }
        )
        self.assertNotIn("THREE_UNCLAMPED_PIXEL_RATIO", codes)

    def test_per_frame_allocation_is_medium(self) -> None:
        r = self._scan(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "function frame() {\n"
                    "  const v = new THREE.Vector3();\n"
                    "  requestAnimationFrame(frame);\n"
                    "}\n"
                )
            }
        )
        sev = {d["code"]: d["severity"] for d in r["defects"]}
        self.assertIn("THREE_PER_FRAME_ALLOCATION", sev)
        self.assertEqual(sev["THREE_PER_FRAME_ALLOCATION"], "MEDIUM")

    def test_ts_return_annotated_and_single_line_methods_detected(self) -> None:
        codes_multiline = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "class Renderer {\n"
                    "  render(dt: number): void {\n"
                    "    const v = new THREE.Vector3();\n"
                    "    requestAnimationFrame(() => this.render(dt));\n"
                    "  }\n"
                    "}\n"
                )
            }
        )
        self.assertIn("THREE_PER_FRAME_ALLOCATION", codes_multiline)

        codes_single_line = self._codes(
            {
                "b.ts": (
                    "import * as THREE from 'three';\n"
                    "class Scene { render(): void { new THREE.Vector3(); } }\n"
                    "requestAnimationFrame(() => {});\n"
                )
            }
        )
        self.assertIn("THREE_PER_FRAME_ALLOCATION", codes_single_line)

    def test_multiline_template_literal_preserves_scope(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "class ShaderMat {\n"
                    "  constructor() {\n"
                    "    const glsl = `\n"
                    "      void main() { gl_FragColor = vec4(1.0); }\n"
                    "    `;\n"
                    "    this.v = new THREE.Vector3();\n"
                    "  }\n"
                    "  render(): void { requestAnimationFrame(() => this.render()); }\n"
                    "}\n"
                )
            }
        )
        self.assertNotIn("THREE_PER_FRAME_ALLOCATION", codes)

    def test_missing_dispose_is_flagged_even_when_pmrem_disposed(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "const renderer = new THREE.WebGLRenderer();\n"
                    "const pmrem = new THREE.PMREMGenerator(renderer);\n"
                    "pmrem.dispose();\n"
                )
            }
        )
        self.assertIn("THREE_MISSING_DISPOSE", codes)

    def test_dispose_present_satisfies_check(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "const renderer = new THREE.WebGLRenderer();\n"
                    "function teardown() { renderer.dispose(); }\n"
                )
            }
        )
        self.assertNotIn("THREE_MISSING_DISPOSE", codes)

    def test_passing_geometry_to_another_owner_is_not_a_dispose_defect(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "export function makeGeo() { return new THREE.BufferGeometry(); }\n"
                )
            }
        )
        self.assertNotIn("THREE_MISSING_DISPOSE", codes)

    def test_module_scope_scratch_is_not_flagged(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "const _v = new THREE.Vector3();\n"
                    "function frame() { requestAnimationFrame(frame); }\n"
                )
            }
        )
        self.assertNotIn("THREE_PER_FRAME_ALLOCATION", codes)

    def test_constructor_scratch_is_not_flagged(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "class Pipeline {\n"
                    "  constructor() {\n"
                    "    this.v = new THREE.Vector3();\n"
                    "  }\n"
                    "  render() { requestAnimationFrame(() => this.render()); }\n"
                    "}\n"
                )
            }
        )
        self.assertNotIn("THREE_PER_FRAME_ALLOCATION", codes)

    def test_shadow_bias_rules_for_lights(self) -> None:
        loader_codes = self._codes(
            {"a.ts": ("import * as THREE from 'three';\nmesh.castShadow = true;\n")}
        )
        self.assertNotIn("THREE_MISSING_SHADOW_BIAS", loader_codes)

        hemi_codes = self._codes(
            {
                "h.ts": (
                    "import * as THREE from 'three';\n"
                    "const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1);\n"
                    "mesh.castShadow = true;\n"
                )
            }
        )
        self.assertNotIn("THREE_MISSING_SHADOW_BIAS", hemi_codes)

        light_codes = self._codes(
            {
                "b.ts": (
                    "import * as THREE from 'three';\n"
                    "const sun = new THREE.DirectionalLight(0xffffff, 2.5);\n"
                    "sun.castShadow = true;\n"
                )
            }
        )
        self.assertIn("THREE_MISSING_SHADOW_BIAS", light_codes)

    def test_gltf_exporter_is_not_flagged(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';\n"
                    "const exporter = new GLTFExporter();\n"
                )
            }
        )
        self.assertNotIn("THREE_UNCOMPRESSED_GLTF", codes)

    def test_jsdoc_example_is_not_code(self) -> None:
        """Ignore code inside multi-line JSDoc comments."""
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "/**\n"
                    " * ```js\n"
                    " * const sun = new THREE.DirectionalLight();\n"
                    " * sun.castShadow = true;\n"
                    " * ```\n"
                    " */\n"
                    "export const x = 1;\n"
                )
            }
        )
        self.assertNotIn("THREE_MISSING_SHADOW_BIAS", codes)

    def test_destructuring_constructor_is_recognised(self) -> None:
        """Handle `constructor( cap, { shadow } ) {` opening two braces."""
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "class Pipeline {\n"
                    "  constructor( cap, { shadow } ) {\n"
                    "    this.v = new THREE.Vector3();\n"
                    "  }\n"
                    "  render() { requestAnimationFrame(() => this.render()); }\n"
                    "}\n"
                )
            }
        )
        self.assertNotIn("THREE_PER_FRAME_ALLOCATION", codes)

    def test_gltf_without_decoders_is_flagged(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';\n"
                    "const loader = new GLTFLoader();\n"
                )
            }
        )
        self.assertIn("THREE_UNCOMPRESSED_GLTF", codes)

    def test_gltf_with_draco_is_clean(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "import * as THREE from 'three';\n"
                    "import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';\n"
                    "const loader = new GLTFLoader().setDRACOLoader(draco);\n"
                )
            }
        )
        self.assertNotIn("THREE_UNCOMPRESSED_GLTF", codes)

    def test_non_three_files_are_not_scanned_for_3d_rules(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "const v = new Vector3();\n"
                    "const renderer = new WebGLRenderer();\n"
                    "renderer.setPixelRatio(window.devicePixelRatio);\n"
                )
            }
        )
        self.assertEqual([c for c in codes if c.startswith("THREE_")], [])

    def test_three_reference_without_import_is_still_scanned(self) -> None:
        codes = self._codes(
            {
                "a.ts": (
                    "const renderer = new THREE.WebGLRenderer();\n"
                    "renderer.setPixelRatio(window.devicePixelRatio);\n"
                )
            }
        )
        self.assertIn("THREE_UNCLAMPED_PIXEL_RATIO", codes)

    def test_python_and_css_files_never_trigger_3d_rules(self) -> None:
        codes = self._codes(
            {
                "a.py": "import THREE\nx = new THREE.Vector3()\n",
                "a.css": ".x{color:red}\n",
            }
        )
        self.assertEqual([c for c in codes if c.startswith("THREE_")], [])

    def test_mjs_and_inline_html_threejs_rules(self) -> None:
        codes = self._codes(
            {
                "scene.mjs": (
                    "import * as THREE from 'three';\n"
                    "const sun = new THREE.DirectionalLight(0xffffff, 2);\n"
                    "sun.castShadow = true;\n"
                ),
                "stage.html": (
                    "<html><body><script type='module'>\n"
                    "import * as THREE from 'three';\n"
                    "const renderer = new THREE.WebGLRenderer();\n"
                    "renderer.shadowMap.type = THREE.PCFSoftShadowMap;\n"
                    "const composer = new EffectComposer(renderer);\n"
                    "composer.addPass(new UnrealBloomPass());\n"
                    "</script></body></html>\n"
                ),
            }
        )
        self.assertIn("THREE_MISSING_SHADOW_BIAS", codes)
        self.assertIn("THREE_DEPRECATED_API", codes)
        self.assertIn("THREE_MISSING_OUTPUT_PASS", codes)
        self.assertIn("THREE_COMPOSER_8BIT_TARGET", codes)

    def test_transition_all_float_blur_and_modern_css_motion(self) -> None:
        r = self._scan(
            {
                "a.css": (
                    ".btn { transition: all 0.2s ease; backdrop-filter: blur(20.5px); }\n"
                    ".rem { backdrop-filter: blur(1.5rem); }\n"
                    ".ok { backdrop-filter: blur(12.5px); }\n"
                    "@view-transition { navigation: auto; }\n"
                    ".reveal { animation-timeline: view(); }\n"
                )
            }
        )
        codes = [d["code"] for d in r["defects"]]
        self.assertIn("TRANSITION_ALL_HAZARD", codes)
        self.assertEqual(codes.count("EXCESSIVE_BLUR_OVERDRAW"), 2)
        self.assertIn("MISSING_REDUCED_MOTION_GUARD", codes)

    def test_wcag_outline_none_and_threejs_room_env_and_clock_delta(self) -> None:
        r = self._scan(
            {
                "a.css": (
                    ".bad:focus-visible { outline: none; }\n"
                    ".good:focus-visible { outline: none; box-shadow: 0 0 0 2px #5e9eff; }\n"
                ),
                "b.ts": (
                    "import * as THREE from 'three';\n"
                    "const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;\n"
                    "const dt = clock.getDelta();\n"
                ),
            }
        )
        codes = [d["code"] for d in r["defects"]]
        self.assertEqual(codes.count("WCAG_OUTLINE_NONE_WITHOUT_REPLACEMENT"), 1)
        self.assertIn("THREE_MISSING_ROOM_ENV_DISPOSE", codes)
        self.assertIn("THREE_UNBOUNDED_CLOCK_DELTA", codes)


class CliGate(unittest.TestCase):
    def _run(
        self, files: dict[str, str], *args: str
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as td:
            for name, body in files.items():
                (Path(td) / name).write_text(body, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-B", str(LINTER), td, *args],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_exit_zero_without_fail_on_even_with_defects(self) -> None:
        r = self._run({"a.css": ".x{transition: width .2s}\n"})
        self.assertEqual(r.returncode, 0)

    def test_fail_on_high_exits_one(self) -> None:
        r = self._run({"a.css": ".x{transition: width .2s}\n"}, "--fail-on", "high")
        self.assertEqual(r.returncode, 1)
        self.assertIn("GATE FAILED", r.stdout)

    def test_fail_on_high_exits_zero_when_clean(self) -> None:
        r = self._run({"a.css": ".x{color:red}\n"}, "--fail-on", "high")
        self.assertEqual(r.returncode, 0)

    def test_missing_target_dir_exits_two_without_100_score(self) -> None:
        tmp = tempfile.mkdtemp()
        shutil.rmtree(tmp)
        r = subprocess.run(
            [sys.executable, "-B", str(LINTER), tmp],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("100 / 100", r.stdout)
        self.assertIn("error:", r.stderr.lower())

    @unittest.skipIf(
        hasattr(os, "geteuid") and os.geteuid() == 0,
        "root can read anything",
    )
    def test_strict_exits_one_on_unreadable_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "secret.css"
            p.write_text(".x{color:red}\n", encoding="utf-8")
            p.chmod(0o000)
            try:
                r = subprocess.run(
                    [sys.executable, "-B", str(LINTER), td, "--strict"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            finally:
                p.chmod(0o644)
            self.assertEqual(r.returncode, 1)
            self.assertIn("GATE FAILED (--strict)", r.stderr)

    def test_json_output_matches_schema_and_sarif_valid(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        r_json = self._run({"a.css": ".x{transition: width .2s}\n"}, "--json")
        self.assertEqual(r_json.returncode, 0)
        payload = json.loads(r_json.stdout)
        jsonschema.validate(instance=payload, schema=schema)

        r_sarif = self._run({"a.css": ".x{transition: width .2s}\n"}, "--sarif")
        self.assertEqual(r_sarif.returncode, 0)
        sarif = json.loads(r_sarif.stdout)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertIn("sarif", sarif["$schema"])
        self.assertIn("2.1.0", sarif["$schema"])
        self.assertGreaterEqual(len(sarif["runs"][0]["results"]), 1)
        self.assertGreaterEqual(len(sarif["runs"][0]["tool"]["driver"]["rules"]), 1)

        sarif_from_fn = build_sarif(payload)
        self.assertEqual(sarif_from_fn["version"], "2.1.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
