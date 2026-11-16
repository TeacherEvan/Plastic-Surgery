# Preflight Scanner Notes — False Positives & Verification Rules

The `preflight_visual_lint.py` scanner is a regex-based static checker. It produces false positives that must be manually triaged — never treat every LOW as a real defect.

## Common False Positives

- **NUMERIC_JITTER_HAZARD on `timer` / `telemetry` / `metric` strings in CSS variable names or JS identifiers.** The regex matches the word, not an actual unstyled number output. Verify: does the target element actually render a changing numeric value? If it's a variable name (`--text-telemetry`) or a timer variable (`autosaveTimer`), ignore.
- **NUMERIC_JITTER_HAZARD on shader code with `float` arithmetic** (e.g., `TARGET_FRAME_MS`, `iTime`). No `font-variant-numeric` applies to GLSL uniforms. Ignore.
- **NUMERIC_JITTER_HAZARD on CSS `text-wrap: balance` or `textWrap: 'balance'`:** Stripped automatically by the scanner before metric matching (`v1.4.0+`); if an element shares a line with a real dynamic readout (e.g., `{account.balance}`), `NUMERIC_JITTER_HAZARD` still fires legitimately.
- **WCAG_SMALL_TARGET_SIZE (`WCAG 2.2 SC 2.5.8`):** Fires when an interactive selector/element explicitly sets `(min-)width` or `(min-)height` below `24px`. Verify whether the target uses the 24 px spacing exception or enlarge to `>= 24x24 CSS px` (`>= 44x44 CSS px` on `any-pointer: coarse`).
- **WCAG_STICKY_FOCUS_OBSCURED (`WCAG 2.2 SC 2.4.11`):** Fires when sticky/fixed top-anchored header/nav chrome exists without `scroll-margin-top` or `scroll-padding-top` anywhere in the project.
- **WCAG_MISSING_CONTRAST_OR_FORCED_COLORS:** Fires when `@media (prefers-reduced-motion)` is present without companion `@media (prefers-contrast)` and `@media (forced-colors)` rules.
- **LAYOUT_THRASHING_ANIMATION** on legitimate composited transforms (`transform`, `opacity`, `border-color`) — the regex over-matches. Confirm the property being animated is `width`, `height`, `top`, `left`, `margin`, or `padding` before treating as HIGH.
- **THREE_PER_FRAME_ALLOCATION** on a zero-argument `new THREE.Vector3()` that is *not* inside the render loop. The rule fires on the whole file when a loop exists somewhere in it. Verify the allocation is on a per-frame path; module-scope scratch objects are fine.
- **THREE_MISSING_DISPOSE** on a file that only *constructs* a shared resource (a renderer factory, a module-level texture). Teardown is often centralised in another module — check the owner before adding a `dispose()`.
- **THREE_MISSING_SHADOW_BIAS** on a scene that sets bias centrally (a light factory or a theme module). Confirm no `shadow.bias` / `normalBias` exists anywhere in the project before treating as real.
- **THREE_UNSET_OUTPUT_COLOR_SPACE** on three r152+ — sRGB output is the default. It is a LOW pin-the-value suggestion, not a defect.
- **THREE_UNCOMPRESSED_GLTF** on an authoring tool or a test fixture where payload size does not matter.
- **THREE_MISSING_RESIZE_HANDLER** on a fixed-size canvas (an offscreen render target, a thumbnail renderer) that legitimately never resizes.

## Verification Workflow

1. Run `python3 .../preflight_visual_lint.py .` after any change.
2. Filter results by `code`. Ignore all LOW hits that match the false-positive patterns above.
3. For any HIGH or non-obvious MEDIUM, open `file_path:line_range` and confirm the exact property being animated.
4. Confirm `font-variant-numeric: tabular-nums` is applied to every real telemetry readout (`#entity-count`, `.prop-row output`, `#bottom-strip`, coordinate strings, timer displays).
5. Confirm no `width`/`height`/`top`/`left`/`margin`/`padding` appears inside any `transition` or `animation` declaration.

## Reduced-Motion Guard Check

Always verify `@media (prefers-reduced-motion: reduce)` exists alongside `@media (prefers-contrast: more)` and `@media (forced-colors: active)`, collapsing spatial translations to `0.01ms` while preserving functional indicators (spinners at reduced speed).

## 3D (Three.js) Check

For WebGL targets, additionally confirm:

1. `renderer.setPixelRatio()` clamps to `[1, 2]`.
2. `renderer.info.render.{calls,triangles}` are inside the tier budget (see `threejs_3d_asset_pipeline.md` §2).
3. `renderer.info.memory.{geometries,textures}` are stable across 20 scene toggles (leak detector).
4. Colour textures are sRGB; normal/ORM/roughness/metallic/AO textures are linear.
5. `OutputPass` is the last composer pass and appears exactly once.
6. Every geometry, material and texture has an explicit `dispose()` path.
7. `THREE.PCFSoftShadowMap` is **not** used — it was removed in r186. Use `THREE.PCFShadowMap`.
8. The scene builds with **zero console warnings**.

## How the `THREE_*` rules were calibrated

The three.js rules were tuned against the **503 real source files** of `three/examples/jsm`
(upstream's own addon library). Before calibration the rules produced **250** findings on
that corpus; most were false positives (module-scope scratch vectors, files that merely
*construct* a geometry they do not own, exporters matching a loader substring). After
calibration the same corpus produces **26** findings, every one of which is a genuine
signal. A linter that cries wolf gets ignored, so scope matters more than coverage.

| Rule | What it now requires | Why the narrower form is right |
| :--- | :--- | :--- |
| `THREE_PER_FRAME_ALLOCATION` | The allocation must sit inside a **function body** (module scope, class fields and constructors excluded) in a file that has a render loop | Module-scope scratch objects (`const _v = new Vector3()`) are the idiomatic three.js pattern — allocated once, reused every frame |
| `THREE_MISSING_DISPOSE` | The file must construct a `WebGLRenderer` | The renderer owns a WebGL context; a file that merely returns a geometry does not own its teardown |
| `THREE_MISSING_SHADOW_BIAS` | The file must **create a light** | A loader that sets `castShadow` on imported meshes does not own the application's shadow bias |
| `THREE_UNCOMPRESSED_GLTF` | A `GLTFLoader` must be **instantiated** | `GLTFExporter` shares the substring but never fetches a compressed payload |
| All file-level rules | Comments and string literals are stripped first | A `castShadow = true` inside a JSDoc example is documentation, not code |

The scope analyser is parenthesis-aware: `constructor( capacity, { shadow } ) {` opens **two**
braces and only the paren-depth-0 one is the constructor body. Getting this wrong silently
re-classified every constructor allocation as a per-frame allocation.

## Asset auditor triage

`scripts/preflight_gltf_budget.py` is a **gate**, not a linter — its findings are measured
against a tier budget, not heuristics. Still read the message: `GLTF_SCALE_SUSPICIOUS` fires
on geometry whose extent is outside `[0.01, 1000]` units, which is right for a metre-unit
asset but worth a second look for a deliberately microscopic or macro-scale one.
