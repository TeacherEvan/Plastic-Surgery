---
name: plastic-surgery
description: "Use when overhauling 2D UI, 3D Three.js, or video visuals."
version: 2.0.0
author: "TeacherEvan, Fenrie (Lea's AI wolf), Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: creative
    tags: [visual, ui-overhaul, design-system, tactile-design, accessibility, animation, 3d, threejs, webgl, gltf, video, ffmpeg, surgical-media]
    requires_tools: [read_file, search_files, browser, vision, terminal]
    related_skills: [surgical-orchestration, surgical-implementation, surgical-audit, surgical-building, surgical-media]
---

# Plastic Surgery — Autonomous 2D UI, 3D Three.js & Video Visual Maximizer

## Overview

Plastic Surgery elevates the visual skin of any **2D UI, GUI, Dashboard, Print Document, 3D Three.js/WebGL Scene, or `surgical-media` Video** ("flat/cheap" -> "tactile, smooth, accessible, and budgeted") while guaranteeing **zero functional regression**. Underlying business logic, state hooks, event handlers, API contracts, accessibility roles, test selectors (`id`, `data-testid`), 3D scene-graph structure (`name`, `userData`, animation clips, asset URLs), and video timing/attribution (`start_sec`, `duration_sec`, `vo_wav`, `words[]`, `sfx_events[]`, `CREDITS.md`) are **strictly immutable**.

### Auxiliary Skill Resources

- [preflight_visual_lint.py](./scripts/preflight_visual_lint.py): Zero-mutation static scanner for compositor layout thrashing, numeric jitter, WCAG 2.2 checks (`2.5.8`, `2.4.11`, contrast/forced-colors/reduced-motion), and `THREE_*` hazards (`--json`, `--sarif`, `--fail-on`).
- [preflight_gltf_budget.py](./scripts/preflight_gltf_budget.py): Zero-mutation glTF 2.0 / GLB auditor (triangles, draw calls, VRAM, material slots, LOD/compression, scale, URI safety).
- [preflight_video_polish.py](./scripts/preflight_video_polish.py): Zero-mutation `surgical-media` storyboard & MP4 auditor (WCAG palette contrast, `linear` easing, safe zones, H.264/`yuv420p`/BT.709/CFR/`+faststart`, EBU R128 loudness, `signalstats`).
- [polish_surgical_media.py](./scripts/polish_surgical_media.py): Non-destructive Mode A (storyboard/3D polish with SHA-256 immutable proof) & Mode B (single-pass FFmpeg + `loudnorm` + `--qc-frames` diff) engine.
- [tactile_tokens_and_surfaces.md](./references/tactile_tokens_and_surfaces.md): Verified sRGB-in-gamut `oklch()` color system, contrast proofs, specular insets, OLED dither, and 6-state tactile button CSS with WCAG 2.2 guards.
- [kinetic_physics_and_springs.md](./references/kinetic_physics_and_springs.md): Exact `expDecay()`, elapsed-time-clamped `stepSpringSubstepped()` (`MAX_FRAME_DT = 0.1`), `AnalyticalSpring`, and keeping per-frame positions out of the reconciler.
- [threejs_3d_asset_pipeline.md](./references/threejs_3d_asset_pipeline.md): End-to-end 3D asset creation pipeline, PBR/IBL lighting, shadow bias, post-processing order, teardown `dispose()`, and Three.js r152–r187+ compatibility.
- [preflight_scanner_notes.md](./references/preflight_scanner_notes.md): Triage rules for scanner false positives and WCAG 2.2 / `THREE_*` / video signals.
- [phase_playbooks_and_checklists.md](./references/phase_playbooks_and_checklists.md): Phase 2 Blueprint template, native GUI rules, 21-item Phase 4 checklist, CDP runtime checks, and static print/video rules.
- [video_post_production.md](./references/video_post_production.md): Mode A (`surgical-media` storyboard/3D polish) & Mode B (single-pass FFmpeg finishing, BT.709, two-pass `loudnorm`, social safe zones).
- [visual-lint-report.schema.json](./schemas/visual-lint-report.schema.json), [gltf-budget-report.schema.json](./schemas/gltf-budget-report.schema.json), [video-polish-report.schema.json](./schemas/video-polish-report.schema.json) & [video-polish-action.schema.json](./schemas/video-polish-action.schema.json): JSON Schema `2020-12` output contracts.

> [!NOTE]
> **Sandbox Portability**: When `.py` or `.sh` execution is restricted, perform all checks deterministically using the checklists in [phase_playbooks_and_checklists.md](./references/phase_playbooks_and_checklists.md) and [preflight_scanner_notes.md](./references/preflight_scanner_notes.md).

---

## When to Use

- A UI, dashboard, settings panel, or game HUD looks flat, dated, or unpolished and needs a tactile visual pass without altering behavior.
- You need measurable rendering guarantees: compositor-only transitions, `tabular-nums`, WCAG 2.2 target/focus/contrast compliance, and reduced-motion safety.
- A **Three.js / WebGL scene** looks flat, washed-out, or plasticky and needs PBR/IBL lighting, tone mapping, or post-processing surgery.
- You are authoring a **new 3D asset** (procedural geometry, PBR maps, LODs, compressed `.glb`) within a strict frame budget.
- A **finished print/PDF document** (CV, one-pager, report, deck) looks generic: use the *Static Document Variant* in [phase_playbooks_and_checklists.md](./references/phase_playbooks_and_checklists.md).
- A **`surgical-media` storyboard/3D scene or rendered MP4** needs visual polish (WCAG palette, filmic grade, non-linear easings, single-pass FFmpeg mastering, BT.709, social safe zones): use [video_post_production.md](./references/video_post_production.md).

## When Not to Use

- Changing business logic, adding features, restructuring state, or fixing functional bugs — use `surgical-implementation`.
- Diagnosing hot-loop CPU stalls or algorithmic stutter before skinning — use `surgical-audit` first.
- Reconstructing 3D/2D building geometry from floorplans or photogrammetry — use `surgical-building`.
- Creating brand-new videos, scripts, research, or VO from scratch — use `surgical-media`.

---

## Hard Technical Limits & Rendering Budgets

### 1. 2D UI, Web DOM, Desktop GUI & Game HUD Budgets

| Metric / Domain | 60 Hz Standard | 120 Hz High-Refresh | Hard Failure Threshold |
| :--- | :--- | :--- | :--- |
| **Total Frame / Render Pass** | `<= 16.67 ms` (`<= 6.67 ms` render) | `<= 8.33 ms` (`<= 3.33 ms` render) | `> 20.0 ms` total / `> 8.0 ms` render |
| **Input-to-Photon / INP** | `<= 16.0 ms` / `<= 100 ms` | `<= 8.33 ms` / `<= 60 ms` | `> 32.0 ms` / `> 200 ms` |
| **Cumulative Layout Shift (CLS)** | `0.00` | `0.00` | `> 0.10` |
| **GPU Blur / High-DPI DPR** | `<= 2` blurs (`<= 16px`), DPR `[1, 2]` | `<= 2` blurs (`<= 12px`), DPR `[1, 2]` | `>= 3` blurs, `> 20px`, or DPR `> 2.0` |
| **Contrast (WCAG / APCA)** | `4.5:1` (`Lc 60`) body / `3.0:1` UI | `7.0:1` (`Lc 75+`) critical telemetry | `< 3.0:1` interactive controls/labels |
| **Interactive Targets (WCAG 2.2)** | `>= 24x24 CSS px` (`>= 44x44` coarse) | `>= 28x28 px` (`>= 4px` gap) desktop | `< 24x24 px` (`SC 2.5.8`) or obscured (`SC 2.4.11`) |

### 2. 3D Scene & Asset Budgets (Three.js / WebGL)

| Tier | Target Device | Triangles | Draw Calls | Texture VRAM | Max Texture | Shadow Maps | Post Passes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Low** | Mid-range mobile / fallback | `<= 60 k` | `<= 80` | `<= 64 MB` | `1024` | `1 x 1024` | `0` (skip composer) |
| **Medium** | Modern mobile / integrated GPU | `<= 300 k` | `<= 250` | `<= 256 MB` | `2048` | `1-2 x 2048` | `<= 3` |
| **High** | Discrete desktop GPU | `<= 1.5 M` | `<= 1000` | `<= 512 MB` | `4096` | `2 x 2048` | `<= 3` |

Always enforce: `renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))`, zero per-frame `new THREE.Vector3()` allocations, stable `renderer.info.memory` across 20 scene toggles, and explicit `dispose()` for textures, materials, geometries, and `WebGLRenderer`.

### 3. Video Finishing & `surgical-media` Budgets

| Stream / Check | Target Contract | Hard Failure Threshold |
| :--- | :--- | :--- |
| **Video Codec & Color** | H.264 High@4.2, `yuv420p`, CFR, `bt709`, `+faststart` | Non-`yuv420p`, VFR, missing `bt709` or `moov` after `mdat` |
| **Audio Mastering** | AAC-LC 48 kHz stereo, `-14.0 +/- 1.0 LUFS`, `<= -1.0 dBTP` | Drift `> 150 ms` vs storyboard or dead air `> 0.6 s` |
| **9:16 Safe Boxes** | Organic `60..930, 180..1540` / Strict `65..888, 288..1248` | Captions, faces, or `CREDITS.md` badges clipped |

---

## Procedure: Five-Phase Surgical Pipeline

Execute phases sequentially; never skip to edits before alignment and pre-op scanning.

### Phase 0: Alignment Gate

1. **Reconnaissance**: Inspect project manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `project.godot`) to identify the Workspace Theme and Rendering Stack.
2. **Verify 3 Axes**:
   - **Axis 1:** `Mobile` vs. `Desktop` vs. `Hybrid`
   - **Axis 2:** `Private` vs. `Commercial`
   - **Axis 3:** `Adult` vs. `All audiences`
3. **Collaboration State**: If any axis cannot be proven from codebase or prompt (except self-evident print/PDF A4 documents), **HALT** and ask those three exact questions plus at most 1–2 polarity follow-ups.

### Phase 1: Investigate & Pre-Op Defect Audit

1. Run the visual preflight scanner (`--json` / `--sarif` supported):

   ```bash
   python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_visual_lint.py" .
   ```

2. Map the workspace domain to 3–5 concrete techniques (perceptual `oklch()` elevation, specular top-edge borders, OLED dither, `expDecay`/sub-stepped springs, `tabular-nums`, PBR + `PMREMGenerator` IBL, tuned shadow bias).
3. Catalog existing visual/3D defects with `file_path:line_range` citations.

### Phase 2: Output the Plastic Surgery Blueprint

Present the structured Blueprint (Alignment Matrix, Token & Contrast System, 6-State Button Spec, Rendering Plan, and Preserved Bindings Check) using the template in [phase_playbooks_and_checklists.md](./references/phase_playbooks_and_checklists.md) before modifying code.

### Phase 3: Implement Visual Skin Only

1. **2D Web / CSS**: Apply verified sRGB-in-gamut `oklch()` tokens (`--accent-primary: oklch(0.70 0.15 260)` paired with `--text-on-accent: oklch(0.12 0.02 265)` for `7.53:1` AAA) and the 6-state `.btn-tactile` contract from [tactile_tokens_and_surfaces.md](./references/tactile_tokens_and_surfaces.md). Include `@media (any-pointer: coarse)`, `@media (prefers-reduced-motion: reduce)`, `@media (prefers-contrast: more)`, `@media (forced-colors: active)`, and `scroll-margin-top` for sticky headers.
2. **Kinetic Motion**: Replace fixed per-frame lerps with `expDecay()` or `stepSpringSubstepped()` from [kinetic_physics_and_springs.md](./references/kinetic_physics_and_springs.md), clamping elapsed time (`MAX_FRAME_DT = 0.1`, `safeDt = Math.min(Math.max(dt, 0), MAX_FRAME_DT)`, `steps = Math.max(1, Math.ceil(safeDt / 0.00833))`), and keep per-frame coordinates out of framework reconciler state.
3. **Native / Desktop GUI**: Pre-render static labels and 9-slice surfaces during init/resize; batch blits; snap final coordinates only at text rasterization.
4. **3D / Three.js & Assets**: Follow D1–D8 in [threejs_3d_asset_pipeline.md](./references/threejs_3d_asset_pipeline.md) (`PCFShadowMap` not `PCFSoftShadowMap`, `PMREMGenerator` + `pmrem.dispose()`, single tuned key light, `RenderPass -> SSAO -> Bloom -> SMAA -> OutputPass` last once, Draco/meshopt + KTX2 decoders, full `dispose()` teardown).
5. **Video / `surgical-media` Polish**: Prefer **Mode A** (polish `style.palette`, `style.grade`, non-linear easings, safe zones, and `.mjs`/`.glb` in `storyboard.json`, then re-render) over **Mode B** (single-pass FFmpeg `filter_complex` + two-pass `loudnorm`) per [video_post_production.md](./references/video_post_production.md).

### Phase 4: Post-Op Verification & Gate

Run automated gates (see `## Verification`), drive mobile `390 px` coarse-pointer + reduced-motion checks, inspect screenshots (`vision_analyze`) using unique capture paths, run the project's E2E suite, and verify all 21 items in [phase_playbooks_and_checklists.md](./references/phase_playbooks_and_checklists.md).

---

## Pitfalls

- **Never cap spring sub-steps instead of frame `dt`.** `Math.min(steps, N)` lets `subDt` exceed the Euler stability limit (`h < 2/omega`); always clamp `dt <= MAX_FRAME_DT = 0.1` first.
- **Pass `--fail-on` in CI.** Plain `preflight_visual_lint.py` exits `0` for reporting unless `--fail-on <level>` or `--strict` (for unreadable files) is passed.
- **Measure `oklch()` contrast in sRGB.** High-chroma `oklch()` values clip out of sRGB gamut (`oklch(0.68 0.19 260)` clips blue `> 1.0`); validate in-gamut linear RGB and composited contrast.
- **Check all three preference queries and `any-pointer: coarse`.** Hybrid touch laptops need `any-pointer: coarse`; WCAG 2.2 baseline expects `prefers-reduced-motion`, `prefers-contrast`, `forced-colors`, and `scroll-margin-top` under sticky bars.
- **Guard against silent CSS & layout traps.** Avoid `* { transition-duration: ... !important }` global overrides, `scale()` on `width: 100%` root containers (`scrollWidth > innerWidth`), single-row mobile nav clipping, `.reveal` hidden without JS fallback, unmerged `twMerge` variant groups, and `backdrop-filter` on repeated cards.
- **Respect 3D resource & color contracts.** Never mix sRGB albedo with linear data maps, never skip `OutputPass` or run tone mapping twice, never rely on `material.dispose()` to free textures, never ignore `pmrem.dispose()` vs `renderer.dispose()`, and check `THREE.REVISION` (`PCFSoftShadowMap` removed in r186).
- **Canvas game HUDs require legibility verification.** If `interactive-ui-design` is available in your harness, run its Step 4.7 HUD legibility pass; otherwise verify before/during/after state clarity and smallest-cell readability directly in screenshots.
- **Video post-production traps.** Never use `ffmpeg -f concat -c copy` on mixed inputs (causes VFR), never place `#` comments inside quoted `-vf` strings, always pair `anullsrc` with generated bumpers, and always write to a new output file in one `filter_complex` pass.

---

## Verification

```bash
# 1. Visual / compositor / WCAG 2.2 / Three.js preflight gate (0 = clean, 1 = defect, 2 = missing target)
python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_visual_lint.py" . --fail-on high --strict

# 2. Machine-readable reports (JSON Schema 2020-12 or SARIF 2.1.0)
python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_visual_lint.py" . --sarif --out reports/visual.sarif

# 3. 3D glTF / GLB asset validation & budget gate
npx @gltf-transform/cli validate path/to/asset.glb
python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_gltf_budget.py" path/to/asset.glb --tier medium --fail-on high

# 4. Video / surgical-media storyboard & MP4 polish gate
python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_video_polish.py" path/to/storyboard.json --fail-on high
python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_video_polish.py" path/to/final.mp4 --measure-audio --fail-on high
```

Confirm runtime DOM invariants (`scrollWidth === innerWidth` at `390 px`, `minHeight >= 44px` under coarse touch emulation, `animationName === "none"` under `prefers-reduced-motion: reduce`, timing authority via `getComputedStyle`) and `renderer.info.{render,memory}` stability, then cite `file:line` evidence for every checked item.

## Related Skills

- `surgical-implementation`: Feature additions, state refactoring, and functional bug fixes.
- `surgical-audit`: Performance, hot-loop, and architecture telemetry before or after skinning.
- `surgical-orchestration`: Multi-worker parallel overhaul coordination.
- `surgical-building`: 3D/2D structural CAD/Blender scene generation before Plastic Surgery polish.
- `surgical-media`: End-to-end social video creation (research, TTS, storyboard, render) enhanced by Plastic Surgery Mode A/B polish.

## Author

TeacherEvan, Fenrie (Lea's AI wolf), Hermes Agent

## License

MIT — see [LICENSE](./LICENSE).
