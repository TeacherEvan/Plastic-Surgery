# Phase Playbooks, Blueprint Template & Verification Checklists

Detailed execution playbooks, copy-paste templates, and checklists extracted from `SKILL.md` for progressive disclosure.

---

## 1. Phase 2: Plastic Surgery Blueprint Template

Output this structured blueprint before modifying any files:

```markdown
# Plastic Surgery Blueprint: [Project / Module Name]

## 1. Alignment & Workspace Theme Lock

- **Collaboration Matrix:** [Mobile | Desktop | Hybrid] + [Private | Commercial] + [Adult | All Audiences]
- **Workspace Theme & Stack:** [Detected Domain Theme] | [Framework / Rendering Engine]
- **Investigated Modern Techniques Selected:**
  1. [Technique 1 + why it elevates this workspace theme]
  2. [Technique 2 + rendering budget impact]
  3. [Technique 3 + interaction/smoothness payoff]

## 2. Perceptual Token & Typography System

| Token | Value (`oklch` / Hex) | Role & Contrast Spec |
| :--- | :--- | :--- |
| `--surface-canvas` | `oklch(0.15 0.018 265)` | Base background void / canvas (`Y ≈ 0.0034`) |
| `--surface-card` | `oklch(0.18 0.020 265)` | Elevated container + `1px` specular top border |
| `--accent-primary` | `oklch(0.70 0.150 260)` | Primary action fill & focus ring (`sRGB` in-gamut, `Y ≈ 0.339`) |
| `--text-on-accent` | `oklch(0.12 0.020 265)` | Foreground on primary accent (`CR = 7.53:1` WCAG AAA) |
| `--text-secondary` | `oklch(0.79 0.015 265)` | Secondary content (`APCA -66.8 Lc`, `LC 65+` AA) |
| `--text-muted` | `oklch(0.66 0.020 265)` | Muted labels / borders (`APCA -45.9 Lc`, `LC 45`) |
| `--text-telemetry` | `oklch(0.98 0.002 265)` | High-priority readouts (`tabular-nums`) |

## 3. Six-State Tactile Button & Control Specification

- **Default:** [Base gradient, `1px` top specular highlight, zero resting 3D transform to save VRAM]
- **Hover (`@media (hover: hover) and (pointer: fine)`):** [`140ms cubic-bezier`, `translate3d(0, -1px, 0)`, opacity-faded glow overlay via `::after`]
- **Active / Pressed:** [`<= 16ms` (`25ms` transition), `translate3d(0, 1px, 0) scale(0.985)`, inset shadow inversion]
- **Focus-Visible:** [`2px solid var(--accent-primary)`, `2px` offset ring; `scroll-margin-top` clears sticky headers]
- **Loading:** [Width-locked bounding box, `.btn-label { visibility: hidden }`, inline `.btn-spinner`, `cursor: wait`]
- **Disabled:** [`opacity: 0.45`, `cursor: not-allowed`, desaturated fill, pointer events preserved]

## 4. Rendering & Smoothness Execution Plan

- **DOM / Layout:** [Compositor-only transforms, `minmax(0, 1fr)` grid locks, `contain: layout style`]
- **Canvas / GUI / Game Loop:** [DPR clamp `[1, 2]`, `dt` exponential decay, cached text/surface blitting]
- **3D / WebGL:** [Tier from budget table, `PMREMGenerator` IBL, one tuned shadow-caster, `OutputPass` last, `renderer.info` assertions]
- **Preserved Bindings Check:** [List of IDs, `data-testid`s, hooks, and callbacks guaranteed untouched]
```

---

## 2. Phase 3: Stack Implementation Notes

### Web / CSS Tactile Surfaces & Accessibility

Canonical CSS for `.btn-tactile` (6-state tactile button, `@media (any-pointer: coarse)` 44 px touch targets, `@media (prefers-reduced-motion: reduce)`, `@media (prefers-contrast: more)`, `@media (forced-colors: active)`, and `scroll-margin-top`) lives in [`tactile_tokens_and_surfaces.md`](./tactile_tokens_and_surfaces.md).

### Kinetic Physics & Smoothness (Canvas / JS / Game Loops)

Canonical TypeScript implementations for `expDecay()`, `stepSpringSubstepped()` (with `MAX_FRAME_DT = 0.1` elapsed-time clamping, never a capped step count), `AnalyticalSpring`, and keeping per-frame positions out of the reconciler live in [`kinetic_physics_and_springs.md`](./kinetic_physics_and_springs.md).

### Native / Desktop / Python GUI Smoothness Rules (Pygame, Qt/PySide, Tkinter, Godot)

- **Zero Per-Frame Font/Surface Instantiation**: Pre-render static labels, 9-slice button states (`default`, `hover`, `pressed`, `disabled`), and drop-shadow surfaces during initialization or resize — never inside `draw()` / `paintEvent()` / `_process()`.
- **Dirty-Rect & Batching**: Group UI draw calls into a single texture atlas or `Surface.blits()` batch to keep render pass duration under `3.33 ms`.
- **Sub-Pixel Jitter Prevention**: Store animated UI coordinates as `float` for spring/decay math, but snap to `Math.round()` / `int()` at final text/border rasterization if the renderer lacks sub-pixel anti-aliasing.

### Three.js / WebGL 3D Scene & Asset Surgery (D1–D8)

Canonical code snippets, material/IBL recipes, shadow tuning, post-processing (`RenderPass -> SSAO/GTAO -> Bloom -> SMAA -> OutputPass`), runtime `renderer.info` assertions, zero-leak `dispose()` teardown, and version table live in [`threejs_3d_asset_pipeline.md`](./threejs_3d_asset_pipeline.md).

---

## 3. Phase 4: Post-Op Verification Checklist & Runtime CDP Recipe

Before concluding any overhaul, verify every applicable item below with concrete `file_path:line` evidence or measured command output:

- [ ] **Linter Clean**: `preflight_visual_lint.py . --fail-on high` exits `0` (zero HIGH compositor/jitter/pixel-ratio defects).
- [ ] **Alignment Verified**: All 3 axes (*Mobile/Desktop*, *Private/Commercial*, *Adult/All audiences*) proven from the codebase or confirmed via Collaboration State.
- [ ] **Functional Integrity**: Zero broken callbacks, state hooks, props, or `data-testid` / `id` selectors.
- [ ] **Compositor Clean**: Zero transitions or `@keyframes` animating `width`, `height`, `top`, `left`, `right`, `bottom`, `margin`, or `padding`.
- [ ] **VRAM & Stacking Safe**: No static `translate3d(0,0,0)` on resting buttons; maximum `2` overlapping `backdrop-filter: blur()` layers (`<= 16px` radius).
- [ ] **Zero Numeric Jitter**: `font-variant-numeric: tabular-nums` (or fixed-width glyph layout in native/game GUIs) applied to all live metrics, timers, and tables.
- [ ] **WCAG 2.2 Preference & Focus Guards**: `@media (prefers-reduced-motion: reduce)`, `@media (prefers-contrast: more)`, `@media (forced-colors: active)`, `>= 24x24 CSS px` interactive targets (`>= 44x44 px` on `any-pointer: coarse`), and `scroll-margin-top` clearing sticky headers (`SC 2.4.11`).
- [ ] **Mobile Fit Proven at 390 px**: `document.documentElement.scrollWidth === innerWidth` AND every nav/control's `getBoundingClientRect().right <= innerWidth`.
- [ ] **Reserved Image Geometry**: Every content image carries `width`/`height` attributes (or fixed `aspect-ratio`) so masonry/grids do not reflow on decode.
- [ ] **Coarse Pointer Emulated**: Assert `>= 44 px` touch targets under `Emulation.setTouchEmulationEnabled` + `Emulation.setDeviceMetricsOverride`, reading `getComputedStyle(el).minHeight`.
- [ ] **Reduced Motion Emulated**: Assert `scroll-behavior: auto`, loop `animation-name: none`, and collapsed transitions under `Emulation.setEmulatedMedia`.
- [ ] **Reveal Content Forced Before Capture**: Add `.in` to every `.reveal` before a full-page screenshot so below-the-fold sections do not appear blank.
- [ ] **Visual QA on Screenshots**: Capture desktop + `390 px` screenshots (saving each capture to a unique filename in the same call) and inspect both with `vision_analyze`.
- [ ] **Repository E2E Suite Executed**: Run the project's own E2E suite (`npx playwright test`, `npm run test:e2e`, etc.) before declaring a visual pass verified.
- [ ] **Timing Authority Measured**: Compare `getComputedStyle(el).transitionDuration` / `.animationDuration` against declared source values to confirm no global `* { ... !important }` rule overrides them.
- [ ] **Measured Report**: State before/after linter score, exit code, and measured viewport/contrast numbers.
- [ ] **3D Budget Held**: `renderer.info.render.{calls,triangles}` within the chosen tier ceiling; `renderer.info.memory.{geometries,textures}` stable across 20 scene toggles.
- [ ] **3D Colour Correct**: Colour textures tagged `SRGBColorSpace`; data textures (normal/ORM/roughness/metallic/AO) tagged `NoColorSpace` (linear); `OutputPass` runs last once.
- [ ] **3D Resources Disposed**: Every geometry, material, texture, and `WebGLRenderer` has an explicit `dispose()` path on teardown.
- [ ] **3D Assets Valid**: `npx @gltf-transform/cli validate` and `preflight_gltf_budget.py <asset.glb> --tier <tier> --fail-on high` pass; Draco/meshopt/KTX2 decoders wired.
- [ ] **3D API Version-Checked**: No deprecated constants (`PCFShadowMap` instead of `PCFSoftShadowMap` removed in r186); zero console warnings; `THREE.REVISION` recorded.

### Runtime CDP Verification Recipe (Web)

```python
# 390 px touch viewport
cdp("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
cdp("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
goto_url("http://127.0.0.1:PORT/?after=1"); wait_for_load()
assert js("document.documentElement.scrollWidth") == js("innerWidth")
assert js("Math.round(document.querySelectorAll('.nav-links a')[3].getBoundingClientRect().right)") <= 390
assert js("getComputedStyle(document.querySelector('.vote-btn')).minHeight") == "44px"

# reduced-motion contract
cdp("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
assert js("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
assert js("getComputedStyle(document.querySelector('.bubble')).animationName") == "none"
cdp("Emulation.setEmulatedMedia", features=[])
```

---

## 4. Static Document Variant — CVs, Reports, One-Pagers (Print / PDF)

Same zero-regression mandate, different instrument: the skin is print CSS plus a headless-Chromium render. Web runtime gates (`390 px`, pointer class, reduced motion, frame budget) do not apply.

1. **Alignment is readable off the artefact — record it, do not halt.** An A4 CV answers the three axes on sight (print + screen, commercial, all audiences).
2. **The preflight linter grades static HTML 100/100 by construction** because motion/compositor defects do not exist; do not confuse a 100 score with a design review.
3. **Use real print gates:** `pdfinfo` page count/size; `pdftotext` clean ATS extraction; `pdftoppm -png -r 110` + vision pass over *every* page; WCAG contrast computed from the hex/in-gamut sRGB tokens.
4. **Delete template furniture:** Remove initials monograms, `01 / 02 / 03` boilerplate numbers, and centred-everything layouts; let typography and real data graphics carry the identity.
5. **Derive graphics from real facts:** Proportional tenure bars or real metrics earn space; stock icons do not. Show the arithmetic in the delivery note.
6. **Verify rendered graphics numerically:** Measure pixel runs against tracks before editing; never adjust correct geometry on an unmeasured reviewer claim.
7. **Zero trailing footer-only pages:** Verify page count with `pdfinfo`; tighten margins or reference blocks instead of shipping a blank overflow page.
