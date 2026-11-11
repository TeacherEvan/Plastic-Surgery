---
name: plastic-surgery
description: "Use when doing a visual UI overhaul without logic drift — including 3D scene and asset work with Three.js."
version: 1.3.0
author: "TeacherEvan, Fenrie (Lea's AI wolf), Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: creative
    tags: [visual, ui-overhaul, design-system, tactile-design, accessibility, animation, 3d, threejs, webgl, gltf]
    requires_tools: [read_file, search_files, browser, vision, terminal]
    related_skills: [surgical-orchestration, surgical-implementation, surgical-audit]
---

# Plastic Surgery — Autonomous UI, GUI, Dashboard & 3D Visual Maximizer

Execute a precision **UI / GUI / Dashboard / 3D Scene** visual overhaul ("Plastic Surgery") that maximizes visual appeal, tactile button physics, animation smoothness, asset fidelity, and workspace-themed modern techniques using a strict **Alignment Gate -> Collaboration State -> Investigate -> Plan -> Implement -> Verify** workflow — while guaranteeing **100% zero functional regression**.

---

## When to Use

- The user says a UI looks flat, dated, cheap, or "not premium" and wants it lifted without touching behaviour.
- You need a measurable visual pass: tactile button states, motion physics, contrast, numeric jitter, reduced-motion coverage.
- A dashboard, settings surface, or game HUD needs polish before a demo or release.
- A **Three.js / WebGL scene** looks flat, dark, washed-out, or plasticky and needs lighting, material, or post-processing surgery.
- The user wants a **3D asset created to full potential**: procedural geometry, a PBR texture set, LODs, and a compressed `.glb` that fits the frame budget.
- A **finished document** — CV, one-pager, report, deck exported to PDF — reads cheap or generic and the owner wants it lifted: use the *Static document variant* below. The web runtime gates (frame budget, 390 px fit, pointer class, reduced motion) do not apply to print.

**Don't use for:** changing business logic, adding features, restructuring state, or fixing a functional bug — use `surgical-implementation` for that. If the complaint is "it stutters" and the cause is a hot loop rather than the visual layer, use `surgical-audit` first; this skill will happily polish a canvas that is still dropping frames.

---

## Overview & Auxiliary Resources

Plastic Surgery is the visual counterpart to `surgical-implementation`: where implementation care ensures logic is correct and robust, Plastic Surgery elevates pixels from "flat and forgettable" to "tight, tactile, and responsive". It treats the visual layer as an isolated surgical skin: the underlying functional structure (state, event bindings, API contracts, test hooks, accessibility roles) is **strictly immutable**.

The same doctrine applies in 3D: the **scene graph** (object names, hierarchy, `userData`, animation clips, asset URLs, event payloads) is immutable surgery-exempt tissue — only **materials, lights, tone mapping, post-processing, camera parameters, and renderer settings** are the mutable skin. Authored *new* 3D assets go through the full creation pipeline in `references/threejs_3d_asset_pipeline.md` so they arrive budgeted, compressed, and disposable.

### Auxiliary Skill Resources (Progressive Disclosure)
- `scripts/preflight_visual_lint.py`: Zero-mutation static scanner detecting layout-thrashing animations, un-budgeted blurs, numeric jitter, reduced-motion gaps, and Three.js/WebGL hazards (`THREE_*` codes).
- `scripts/preflight_gltf_budget.py`: Zero-mutation glTF/GLB asset auditor — triangle count, draw calls, texture VRAM, material slots, texture dimensions, LOD coverage, compression coverage and structural defects against a device tier.
- `references/tactile_tokens_and_surfaces.md`: Perceptual `oklch()` color system, APCA/WCAG contrast proofs, specular top-edge insets, sub-perceptual OLED dithering, and 6-state tactile button specification.
- `references/kinetic_physics_and_springs.md`: Exact `expDecay()` stability proofs, dynamic sub-stepped symplectic spring integrators, analytical harmonic oscillators, frame budget tables, and §5 on keeping per-frame positions out of the component reconciler (membership in state, position in a mutable map, direct DOM writer, layout properties written only on change).
- `references/threejs_3d_asset_pipeline.md`: End-to-end 3D asset creation (concept -> blockout -> UV -> PBR bake -> LOD -> glTF -> Draco/KTX2 -> runtime), Three.js material/lighting/post-processing recipes, shader customisation, procedural geometry & instancing, verified version compatibility, and render budget tiers.
- `references/preflight_scanner_notes.md`: Known false positives of the linter (CSS variable names, GLSL uniforms, timer identifiers, three.js module boundaries) and how to triage them before acting.

> [!NOTE]
> **Sandbox Portability**: In environments where `.py` or `.sh` script execution is restricted (e.g. cloud chat sandboxes), all audit checks can be performed deterministically via manual inspection using the checklists in this specification and the bundled reference docs.

---

## 1. Core Surgical Mandate: Zero Functional Regression

When operating on an existing codebase, enforce an absolute separation between **Visual Skin / Presentation (Mutable)** and **Core Logic / State (Immutable)**:

1. **Preserve All Functional Bindings**: Never delete, rename, or break event handlers (`onClick`, `onSubmit`, signal connections, IPC channels, Godot/Unity callbacks), state hooks, form `name` attributes, accessibility attributes (`aria-*`, `role`), or test selectors (`id`, `data-testid`, `data-cy`).
2. **Preserve Data Contracts**: Never alter API payload shapes, database queries, store schemas, or component prop interfaces unless strictly adding optional visual-only props (`variant`, `size`, `isLoading`).
3. **Isolate Visual Layers**: Encapsulate shaders, particle loops, spring solvers, and styling tokens in dedicated presentation modules or CSS layers (`@layer tokens, base, components, utilities`) so they never pollute domain logic.

---

## 2. Hard Technical Specifications & Rendering Limits

Every implementation must satisfy these measurable engineering budgets across Web DOM, Canvas/WebGL, Desktop GUI, and Game UI stacks:

| Metric / Domain | 60 Hz Standard Budget | 120 Hz High-Refresh Budget | Hard Ceiling / Failure Threshold |
| :--- | :--- | :--- | :--- |
| **Total Frame Time** | `<= 16.67 ms` | `<= 8.33 ms` | `> 20.0 ms` (Dropped frames / visible stutter) |
| **Logic / Update Pass** | `<= 10.0 ms` | `<= 5.0 ms` | `> 12.0 ms` (Main-thread / game-loop stall) |
| **Render / Composite Pass** | `<= 6.67 ms` | `<= 3.33 ms` | `> 8.0 ms` (Overdraw / layout thrashing) |
| **Button Input-to-Photon** | `<= 16.0 ms` (1 frame) | `<= 8.33 ms` (1 frame) | `> 32.0 ms` (Perceived sluggish/dead control) |
| **Interaction to Next Paint (INP)** | `<= 100 ms` | `<= 60 ms` | `> 200 ms` (Core Web Vitals fail) |
| **Cumulative Layout Shift (CLS)** | `0.00` | `0.00` | `> 0.10` (Unreserved dynamic bounds / jitter) |
| **GPU Blur / Overdraw** | `<= 2` layers (`8px-16px` radius) | `<= 2` layers (`8px-12px` radius) | `>= 3` overlapping blurs or `> 20px` radius |
| **High-DPI Buffer Scaling** | `clamp(DPR, 1.0, 2.0)` | `clamp(DPR, 1.0, 2.0)` | `DPR > 2.0` on 4K/mobile (Fill-rate collapse) |
| **Contrast (APCA / WCAG)** | `4.5:1` (`LC 60`) body / `3.0:1` (`LC 45`) UI | `7.0:1` (`LC 75+`) critical telemetry | `< 3.0:1` on interactive controls or labels |
| **Interactive Hit Targets** | `44x44 CSS px` (`48x48 dp`) touch | `28x28 px` (`>= 4px` gap) desktop pointer | `< 24x24 px` or `0px` inter-button clearance |

### 2.1 3D Scene & Asset Budgets (Three.js / WebGL tiers)

The tier is chosen from the Phase 0 alignment axes (*Mobile/Desktop* drives the triangle and
texture ceilings). Full derivation, authoring rules and measurement harnesses live in
`references/threejs_3d_asset_pipeline.md`.

| Tier | Target device | Visible triangles | Draw calls | Texture VRAM | Max texture | Shadow maps | Post passes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Low** | Mid-range mobile / WebGL fallback | `<= 60 k` | `<= 80` | `<= 64 MB` | `1024` | `1 x 1024` | `0` (skip composer) |
| **Medium** | Modern mobile / integrated desktop GPU | `<= 300 k` | `<= 250` | `<= 256 MB` | `2048` | `1-2 x 2048` | `<= 3` |
| **High** | Discrete desktop GPU | `<= 1.5 M` | `<= 1000` | `<= 512 MB` | `4096` | `2 x 2048` | `<= 3` |

Additional 3D hard limits: `renderer.setPixelRatio(clamp(DPR, 1, 2))` always; per-frame
`new THREE.Vector3()` allocations `= 0`; `renderer.info.memory.{geometries,textures}` counts
stable across 20 scene toggles; every GPU-owning resource has an explicit `dispose()` path.

---

## 3. Master Execution Pipeline

Execute these phases in strict sequential order. Do not skip directly to code generation.

### Phase 0: Codebase Alignment Check & Conditional Collaboration State

1. **Silent Codebase Reconnaissance**:
   - Inspect project manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `project.godot`, etc.), entry points, theme files, and existing UI components.
   - Extract the **Workspace Theme** (domain subject, existing color palette, visual metaphor, copywriting tone) and **Rendering Stack** (React/Next.js, Svelte, Tailwind, Canvas/WebGL, Pygame/Arcade, Qt/PySide, Tkinter, Godot, Unity, or Curses/TUI).
2. **Evaluate the 3 Alignment Axes**:
   Determine whether the codebase and user prompt explicitly establish:
   - **Axis 1:** `Mobile` vs. `Desktop` vs. `Hybrid`
   - **Axis 2:** `Private` vs. `Commercial`
   - **Axis 3:** `Adult` vs. `All audiences`
3. **Trigger Collaboration State (MANDATORY IF UNALIGNED)**:
   If **any** axis cannot be verified with high confidence from the codebase or prompt, **HALT immediately**. Do not investigate techniques, do not plan, and do not write code. Enter the **Collaboration State** starting with these exact three questions:
   - **1. Mobile/Desktop:** Is this targeting mobile touch viewports, desktop pointer/multi-window environments, or a responsive hybrid?
   - **2. Private/Commercial:** Is this a private/internal tool (allowing experimental, dense, bespoke aesthetics) or a commercial release (requiring strict accessibility, broad compatibility, and conversion polish)?
   - **3. Adult/All audiences:** Is this aimed at an adult/specialized demographic (permitting dark industrial, gritty, high-density, or mature themes) or all audiences (requiring approachable, high-clarity, universally safe design)?
4. **Adaptive Follow-Up**:
   - Once the user answers the initial three questions, synthesize their constraints and ask at most **1 to 2 targeted follow-up questions** if specific aesthetic polarity (e.g., dark-first obsidian vs. daylight editorial, shader intensity, or information density) needs lock-in.
   - Once aligned, proceed immediately to **Phase 1 (Investigate)**.

---

### Phase 1: Investigate Modern Techniques & Pre-Op Defect Audit

1. **Pre-Op Automated Telemetry Scan**:
   Run the visual scanner from the skill directory against the target workspace:
   ```bash
   python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_visual_lint.py" .
   ```
2. **Workspace Theme Mapping**:
   - Map the domain vertical (*AI Telemetry*, *Fintech Ledger*, *Cyberpunk/Terminal TUI*, *Hardware Synth*, *3D Product Configurator*, etc.) to 3–5 cutting-edge visual techniques:
     - **Surface & Depth:** `oklch()` tonal lightness elevation (`+3%` per z-layer), top-edge specular borders (`inset 0 1px 0 oklch(1 0 0 / 0.14)`), sub-perceptual $1.5\%$ SVG anti-banding dither, or OLED bezel shadows.
     - **Tactile & Kinetic Motion:** Frame-rate independent exponential decay, dynamic sub-stepped spring solvers, FLIP layout animations, and staggered entrances (`15-25 ms` stagger, max `250 ms`).
     - **Telemetry & Readouts:** `font-variant-numeric: tabular-nums` column locking, canvas micro-sparklines, glowing semantic status pips (`0 0 8px var(--status-nominal)`), and tactile keycap hints (`<kbd>`).
     - **3D Material & Light (WebGL stacks):** physically-based PBR (`MeshStandardMaterial` default), IBL via `PMREMGenerator` + `RoomEnvironment`, one shadow-casting key light with tuned `bias`/`normalBias`, `ACESFilmic`/`AgX` tone mapping, and a bounded post chain (SSAO -> Bloom -> `OutputPass` last).
3. **Pre-Op Defect Catalog**:
   - Catalog all visual and kinetic bugs with `file_path:line_range` references: layout-thrashing animations, missing `:active` button depression, hover sticking on touch devices, unreserved dynamic bounds, or font allocations in draw loops.
   - For WebGL/Three.js targets, additionally catalog: unclamped `devicePixelRatio`, per-frame scratch-object allocation, missing `dispose()` paths, sRGB/linear texture mislabelling, double tone-mapping, missing Draco/KTX2 decoders, and shadow bias gaps.

---

### Phase 2: Output the Plastic Surgery Blueprint

Output a structured **Plastic Surgery Blueprint** before modifying any files:

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
| `--surface-canvas` | `oklch(0.15 0.018 265)` | Base background void / canvas (Y ≈ 0.0034) |
| `--surface-card` | `oklch(0.18 0.020 265)` | Elevated container + `1px` specular top border |
| `--accent-primary` | `oklch(0.68 0.190 260)` | Primary action fill & focus ring |
| `--text-on-accent` | `oklch(0.12 0.020 265)` | Foreground on primary accent (CR = 7.05:1 AAA) |
| `--text-secondary` | `oklch(0.79 0.015 265)` | Secondary content (APCA -66.8 Lc, LC 65+ AA) |
| `--text-muted` | `oklch(0.66 0.020 265)` | Muted labels / borders (APCA -45.9 Lc, LC 45) |
| `--text-telemetry` | `oklch(0.98 0.002 265)` | High-priority readouts (tabular-nums) |

## 3. Six-State Tactile Button & Control Specification
- **Default:** [Base gradient, `1px` top specular highlight, zero resting 3D transform to save VRAM]
- **Hover (`@media (hover: hover) and (pointer: fine)`):** [`140ms cubic-bezier`, `translate3d(0, -1px, 0)`, opacity-faded glow overlay via `::after`]
- **Active / Pressed:** [`<= 16ms` (`25ms` transition), `translate3d(0, 1px, 0) scale(0.985)`, inset shadow inversion]
- **Focus-Visible:** [`2px solid var(--accent-primary)`, `2px` offset ring]
- **Loading:** [Width-locked bounding box, `.btn-label { visibility: hidden }`, inline `.btn-spinner`, `cursor: wait`]
- **Disabled:** [`opacity: 0.45`, `cursor: not-allowed`, desaturated fill, pointer events preserved]

## 4. Rendering & Smoothness Execution Plan
- **DOM / Layout:** [Compositor-only transforms, `minmax(0, 1fr)` grid locks, `contain: layout style`]
- **Canvas / GUI / Game Loop:** [DPR clamp `[1, 2]`, `dt` exponential decay, cached text/surface blitting]
- **3D / WebGL:** [Tier from §2.1, `PMREMGenerator` IBL, one tuned shadow-caster, `OutputPass` last, `renderer.info` assertions]
- **Preserved Bindings Check:** [List of IDs, `data-testid`s, hooks, and callbacks guaranteed untouched]
```

---

### Phase 3: Implement the Overhaul (Web, Desktop GUI, Game & 3D Stacks)

Apply planned changes cleanly and modularly across the target stack:

#### A. Production-Ready Six-State Tactile Button (Web / CSS)
```css
.btn-surgical {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 40px; /* Expands to 44px on coarse touch pointer viewports */
  min-width: 80px;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-family: inherit;
  font-size: var(--font-sm, 0.875rem);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
  color: var(--text-primary, oklch(0.96 0.005 265));
  background: linear-gradient(180deg, oklch(0.26 0.02 265) 0%, oklch(0.20 0.02 265) 100%);
  border: 1px solid oklch(1 0 0 / 0.12);
  box-shadow:
    inset 0 1px 0 0 oklch(1 0 0 / 0.14),
    0 1px 2px 0 oklch(0 0 0 / 0.45),
    0 4px 8px -2px oklch(0 0 0 / 0.25);
  /* Omit resting translate3d(0,0,0) to prevent permanent GPU backing layer allocation */
  user-select: none;
  touch-action: manipulation;
  cursor: pointer;
  -webkit-font-smoothing: antialiased;
  transition:
    transform 140ms cubic-bezier(0.22, 1, 0.36, 1),
    border-color 140ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* Compositor-accelerated hover elevation via opacity */
.btn-surgical::after {
  content: "";
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: linear-gradient(180deg, oklch(1 0 0 / 0.06) 0%, oklch(1 0 0 / 0.00) 100%);
  box-shadow:
    inset 0 1px 0 0 oklch(1 0 0 / 0.22),
    0 4px 12px -2px oklch(0 0 0 / 0.5),
    0 0 16px -4px oklch(0.68 0.19 260 / 0.35);
  opacity: 0;
  pointer-events: none;
  transition: opacity 140ms cubic-bezier(0.22, 1, 0.36, 1);
}

@media (pointer: coarse) {
  .btn-surgical {
    min-height: 44px;
    padding: 0.625rem 1.125rem;
  }
}

@media (hover: hover) and (pointer: fine) {
  .btn-surgical:hover:not(:disabled):not([aria-disabled="true"]):not([data-loading="true"]) {
    border-color: oklch(1 0 0 / 0.24);
    transform: translate3d(0, -1px, 0) scale(1.005);
  }
  .btn-surgical:hover:not(:disabled):not([aria-disabled="true"]):not([data-loading="true"])::after {
    opacity: 1;
  }
}

.btn-surgical:active:not(:disabled):not([aria-disabled="true"]):not([data-loading="true"]) {
  transition-duration: 25ms;
  transform: translate3d(0, 1px, 0) scale(0.985);
  box-shadow:
    inset 0 2px 4px 0 oklch(0 0 0 / 0.65),
    0 1px 1px 0 oklch(0 0 0 / 0.3);
}
.btn-surgical:active:not(:disabled):not([aria-disabled="true"]):not([data-loading="true"])::after {
  opacity: 0;
}

.btn-surgical:focus-visible {
  outline: 2px solid var(--accent-primary, oklch(0.68 0.19 260));
  outline-offset: 2px;
}

.btn-surgical:disabled,
.btn-surgical[aria-disabled="true"] {
  opacity: 0.45;
  cursor: not-allowed;
  filter: grayscale(40%);
  box-shadow: none;
  transform: none !important;
}

/* Width-locked loading state */
.btn-surgical[data-loading="true"] {
  cursor: wait;
}

.btn-surgical[data-loading="true"] .btn-label {
  visibility: hidden;
}

.btn-surgical .btn-spinner {
  display: none;
  position: absolute;
  width: 1rem;
  height: 1rem;
  border: 2px solid oklch(1 0 0 / 0.2);
  border-top-color: var(--text-primary);
  border-radius: 50%;
  animation: btn-spin 600ms linear infinite;
}

.btn-surgical[data-loading="true"] .btn-spinner {
  display: block;
}

@keyframes btn-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .btn-surgical,
  .btn-surgical::after {
    transition-duration: 0.01ms !important;
    transform: none !important;
  }
  .btn-surgical .btn-spinner {
    animation-duration: 1.5s;
  }
}
```

#### B. Kinetic Physics & Smoothness (Canvas / JS / Game Loops)
Never use fixed per-frame multipliers (`val += (target - val) * 0.1`). Use delta-time exponential decay or dynamic sub-stepped spring integration (see `references/kinetic_physics_and_springs.md` for analytical solutions):

```typescript
// 1. Frame-Rate Independent Exponential Decay (Unconditionally Bounded)
export function expDecay(current: number, target: number, decay = 18, dt: number): number {
  const safeDt = Math.max(dt, 0); // No upper clamp: exact math converges smoothly
  return target + (current - target) * Math.exp(-decay * safeDt);
}

// 2. Dynamically Sub-stepped Spring Step (Numerically Stable at All Framerates)
export function stepSpringSubstepped(
  pos: number,
  vel: number,
  target: number,
  stiffness = 350,
  damping = 28,
  dt = 1 / 60
): [number, number] {
  // Clamp ELAPSED TIME, not the step count. A capped step count lets subDt grow
  // past the explicit-Euler stability bound (h < 2/ω ≈ 0.107 s at these
  // defaults) after a tab switch or resume, and the integrator diverges.
  const MAX_FRAME_DT = 0.1; // 10 fps floor; beyond this the frame is a resume, not a frame
  const safeDt = Math.min(Math.max(dt, 0), MAX_FRAME_DT);
  const MAX_SUB_DT = 0.00833; // 120Hz precision ceiling
  const steps = Math.max(1, Math.ceil(safeDt / MAX_SUB_DT));
  const subDt = safeDt / steps;

  for (let i = 0; i < steps; i++) {
    const accel = -stiffness * (pos - target) - damping * vel;
    vel += accel * subDt;
    pos += vel * subDt;
  }

  if (Math.abs(pos - target) < 0.001 && Math.abs(vel) < 0.005) {
    return [target, 0];
  }

  return [pos, vel];
}
```

**Converting a legacy per-frame lerp.** Do not guess the new constant: a per-frame
factor `p` at 60 fps is `λ = −ln(p) × 60` per second, so `0.02 → 1.21`, `0.1 → 2.19`,
`0.9 → 6.32`, `0.92 → 5.00`. Pass elapsed seconds and the motion keeps its 60 Hz feel
while becoming identical at 120 Hz. Convert **every** decay in the loop (hue, shake,
pulse), not only the one the linter flagged — a half-converted loop still drifts on a
high-refresh display. If the loop clamps elapsed time (e.g. 100 ms) to avoid a
post-resume snap, that is a deliberate policy rather than a maths fix; never clamp the
spring sub-step *count* instead.

#### C. Native / Desktop / Python GUI Smoothness Rules (Pygame, Qt/PySide, Tkinter, Godot)
- **Zero Per-Frame Font/Surface Instantiation**: Pre-render static labels, 9-slice button states (`default`, `hover`, `pressed`, `disabled`), and drop-shadow surfaces during initialization or resize—never inside `draw()` / `paintEvent()` / `_process()`.
- **Dirty-Rect & Batching**: Group UI draw calls into a single texture atlas or `Surface.blits()` batch to keep render pass duration under `3.33 ms`.
- **Sub-Pixel Jitter Prevention**: Store animated UI coordinates as `float` for spring/decay math, but snap to `Math.round()` / `int()` at final text/border rasterization if the renderer lacks sub-pixel anti-aliasing.

#### D. Three.js / WebGL 3D Scene & Asset Surgery

Full pipeline, rationale and copy-paste templates: `references/threejs_3d_asset_pipeline.md`.

**D1 — Renderer contract (never skip the clamp):**
```typescript
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance', stencil: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); // clamp [1, 2]
renderer.outputColorSpace = THREE.SRGBColorSpace;                  // sRGB colour, linear data
renderer.toneMapping = THREE.ACESFilmicToneMapping;                // or AgX / Neutral
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap; // PCFSoftShadowMap was removed in r186
```

**D2 — IBL instead of guessed light intensities** (the fastest realism upgrade):
```typescript
const pmrem = new THREE.PMREMGenerator(renderer);
const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environment = env;
scene.environmentIntensity = 1.0;
scene.background = env;
scene.backgroundBlurriness = 0.6;
pmrem.dispose(); // PMREM render targets are GPU memory
```

**D3 — One tuned shadow caster** (shadows are the #1 scene cost):
```typescript
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);   // 1024 on Low tier
sun.shadow.camera.left = -20; sun.shadow.camera.right = 20;   // tight frustum
sun.shadow.camera.top = 20;   sun.shadow.camera.bottom = -20;
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.02; // scale to world units
sun.shadow.radius = 2;
renderer.shadowMap.autoUpdate = false;   // static scenes: set needsUpdate on change only
```

**D4 — Asset creation pipeline** (when producing a *new* 3D asset, not polishing one):
`Concept & Budget -> Blockout -> Detail (chamfer 2-3% on hard edges) -> UV & texel density -> PBR bake (albedo sRGB + normal OpenGL +Y + ORM linear) -> LOD (100/40/15%) -> glTF 2.0 export (meters, +Y up, applied transforms) -> Draco/meshopt + KTX2 -> runtime load with decoders -> budget audit`.
Budgets per tier: see §2.1. Validate with `npx @gltf-transform/cli validate model.glb`, then **gate** it:

```bash
python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_gltf_budget.py" model.glb --tier medium --fail-on high
echo "exit=$?"   # 0 = within budget, 1 = HIGH defect present
```

The auditor measures what the asset will cost at runtime — triangles, draw calls, texture
VRAM (mip chain included), material slots, texture dimensions — and flags structural defects
(negative-scale nodes, missing LODs, uncompressed geometry/textures, metre-scale violations).


**D5 — Runtime budget assertions (the 3D equivalent of the preflight linter):**
```typescript
const { calls, triangles } = renderer.info.render;          // per-frame
const { geometries, textures } = renderer.info.memory;      // cumulative -> leak detector
if (calls > budget.maxDrawCalls) throw new Error(`draw calls ${calls}`);
if (triangles > budget.maxTriangles) throw new Error(`triangles ${triangles}`);
```

**D6 — Zero-leak teardown** (mandatory in every SPA route change):
```typescript
root.traverse((obj) => {
  const mesh = obj as THREE.Mesh;
  mesh.geometry?.dispose();
  const mat = mesh.material as THREE.Material | THREE.Material[] | undefined;
  (Array.isArray(mat) ? mat : mat ? [mat] : []).forEach((m) => {
    for (const key of Object.keys(m)) {
      const value = (m as unknown as Record<string, unknown>)[key];
      if (value instanceof THREE.Texture) value.dispose(); // material.dispose() does NOT free textures
    }
    m.dispose();
  });
});
root.parent?.remove(root);
```

**D7 — Post-processing order (wrong order = wrong colours):**
`RenderPass -> SSAO/GTAO -> Bloom -> SMAA -> OutputPass (LAST, exactly once)` on a `HalfFloatType` render target with `samples: 4` for MSAA. Cap at 3 passes; skip the composer entirely on Low tier.

**D8 — 3D reduced motion:** honour `prefers-reduced-motion` by disabling auto-orbit, idle camera drift, and spring-damped camera easing — but keep state changes legible.

---

### Phase 4: Post-Op Verification Checklist

Before concluding the task, run the automated linter (or execute manual verification if in a script-restricted environment) and verify every item below:

- [ ] **Linter Clean**: `python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_visual_lint.py" .` yields 0 high-severity compositor/jitter defects.
- [ ] **Alignment Verified**: All 3 axes (*Mobile/Desktop*, *Private/Commercial*, *Adult/All audiences*) were either proven from the codebase or confirmed via the Collaboration State.
- [ ] **Functional Integrity**: Zero broken callbacks, state hooks, props, or `data-testid` / `id` selectors.
- [ ] **Compositor Clean**: Zero transitions or keyframes animating `width`, `height`, `top`, `left`, `margin`, or `padding`.
- [ ] **VRAM & Stacking Safe**: No static `translate3d(0,0,0)` on resting buttons; maximum `2` overlapping `backdrop-filter: blur()` layers (`<= 16px` radius).
- [ ] **Zero Numeric Jitter**: `font-variant-numeric: tabular-nums` (or fixed-width glyph layout in native/game GUIs) applied to all live metrics, timers, and tables.
- [ ] **Reduced-Motion Guard**: `@media (prefers-reduced-motion: reduce)` collapses spatial translations to `0.01ms` while preserving gentle indicator/spinner animations.
- [ ] **Mobile Fit Proven at 390 px**: `document.documentElement.scrollWidth === innerWidth` AND every nav/control's `getBoundingClientRect().right <= innerWidth`. A nav can pass the scrollWidth test while its last link sits past the viewport inside an `overflow-x:auto` container — measure the links, not just the page.
- [ ] **Reserved Image Geometry**: every content image carries `width`/`height` attributes (or a fixed `aspect-ratio`) so masonry/grids do not reflow on decode. For user uploads, store natural dimensions at resize time and render them.
- [ ] **Coarse Pointer Emulated**: assert 44 px touch targets under a real coarse-pointer context — `Emulation.setTouchEmulationEnabled` plus `Emulation.setDeviceMetricsOverride`, then read `getComputedStyle(el).minHeight` for each interactive class.
- [ ] **Reduced Motion Emulated**: `Emulation.setEmulatedMedia` with `prefers-reduced-motion: reduce`; assert `scroll-behavior:auto`, bubble/loop `animation-name:none`, and collapsed transition durations.
- [ ] **Reveal Content Forced Before Capture**: if the page uses scroll reveals, add `.in` to every `.reveal` before a full-page screenshot; IntersectionObserver does not fire below the fold, so unrevealed sections look missing.
- [ ] **Visual QA on Screenshots**: capture desktop + 390 px after the pass and inspect both with `vision_analyze`. CSS metrics cannot see a cramped nav or a caption lost against busy artwork; a fixed element can also look clipped when the screenshot crop is shorter than the viewport — confirm any suspected clip numerically before editing.
- [ ] **Repository E2E Suite Executed**: run the project's own end-to-end suite (`npx playwright test`, `npm run test:e2e`, whatever `AGENTS.md`/CI names) before declaring a visual change verified. Component and unit tests never exercise the browser's cascade, viewport fit, pointer class or touch routing, so a green unit suite says nothing about a restyle. If every spec fails at `browserType.launch` with `Executable doesn't exist`, the browser revision is missing, not the UI broken — `npx playwright install <project>` and re-run before reading any of it as a behavioural failure.
- [ ] **Timing Authority Measured**: for two or three elements with a *declared* duration, compare `getComputedStyle(el).transitionDuration` / `.animationDuration` against the value written in the source. If they all compute to the same number, the design system is not in effect and every duration in the repo is decorative.
- [ ] **Measured Report**: state the before/after linter score, gate exit code, and the viewport numbers. Adjectives are not evidence.
- [ ] **3D Budget Held**: `renderer.info.render.{calls,triangles}` within the §2.1 tier ceiling; `renderer.info.memory.{geometries,textures}` stable across 20 scene toggles.
- [ ] **3D Colour Correct**: colour textures tagged sRGB, data textures (normal/ORM/roughness/metallic/AO) tagged linear; `OutputPass` last so tone mapping runs exactly once.
- [ ] **3D Resources Disposed**: every geometry, material and texture created by the scene has an explicit `dispose()` path on teardown.
- [ ] **3D Assets Valid**: `gltf-transform validate` passes; `preflight_gltf_budget.py` reports zero HIGH defects at the chosen tier; decoders (Draco/meshopt/KTX2) wired; LODs and texel density consistent.
- [ ] **3D API Version-Checked**: no deprecated constants in use (e.g. `PCFSoftShadowMap` was removed in r186 — use `PCFShadowMap`); the scene builds with **zero console warnings**; `THREE.REVISION` recorded in the ticket.

---

## Static document variant — CVs, reports, one-pagers (print/PDF)

Same mandate, different instrument: the skin is print CSS plus a headless-Chromium render. Every runtime gate above is inapplicable here, and applying them substitutes theatre for verification.

1. **Alignment is readable off the artefact — record it, do not halt.** An A4 CV answers the three axes on sight (print + screen, commercial, all audiences). Write the matrix into the blueprint; reserve the Collaboration State for artefacts that are genuinely ambiguous.
2. **The preflight linter grades static HTML 100/100 by construction.** It scans for motion, compositor and jitter defects a print document cannot contain, so a perfect score proves only that those specific defects are absent — it is not a design review.
3. **The real gates are print gates:** `pdfinfo` page count and page size; `pdftotext` clean extraction (this is the ATS test); `pdftoppm -png -r 110` plus a vision pass over *every* page; WCAG ratios computed from the hex tokens rather than eyeballed.
4. **Template furniture is the tell.** An initials monogram in the masthead, `01 / 02 / 03` section numbering, and centred-everything read as a fill-in-the-blank template however clean the spacing. Delete them; let the name, the type pairing and one real data graphic carry the identity.
5. **Derive the graphic from the subject's own facts.** A proportional tenure bar (employer A 2.5 y against employer B 25.75 y) earns its space; stock icons and decorative charts do not. Compute segment widths from the dates and show the arithmetic in the delivery note.
6. **Verify the graphic numerically before trusting anyone's eye.** Measure the rendered shape — scan the page bitmap for runs of the accent colour and compare each bar against its track (a 48 px run inside a 567 px track is 8.5 %, not "about a quarter"). A reviewer claiming "the bars aren't to scale" is stating a hypothesis; measure, then fix or reject it. Editing on an unmeasured claim is how a correct chart gets broken.
7. **A trailing page holding only the footer is a failure, not a rounding error.** `pdfinfo` is the check. Fix it by tightening the reference block and the closing margins, never by shipping the blank page.

## Pitfalls

- **A capped sub-step count is not stability.** Any spring integrator must clamp the *frame delta*; a `Math.min(steps, N)` guard silently grows `subDt` and diverges after a tab resume. Clamp `dt` at the loop, then sub-step as finely as needed.
- **The preflight linter only exits non-zero with `--fail-on`.** A plain run prints a score and exits 0 — a CI job wired to the bare command will always be green.
- **`backdrop-filter` cost is per-layer, not per-radius.** Two 16 px blurs stacked cost more than one 40 px blur; the linter's 16 px rule is a proxy, not a budget proof.
- **`pointer: coarse` is not the same as "mobile".** Hybrid laptops report a fine pointer and a touchscreen; the 44 px touch target must be driven by `any-pointer: coarse` if both matter.
- **Preserved bindings are the contract.** Renaming a `data-testid`, an `aria-*` attribute, or a form `name` is a functional regression even when the page looks perfect.
- **Do not "fix" a stutter by adding `will-change`.** A permanent compositor layer costs VRAM on every element that has it; scope it to the interaction and remove it after.
- **Contrast claims from `oklch()` have to be measured.** Convert to sRGB and compute APCA/WCAG against the actual composited background, including gradients and overlays — not the token's nominal value.
- **A one-row mobile nav clips silently.** Brand + four links + an account pill exceeds 390 px even when each item is small; the links overflow inside a scroller, so the page never shows horizontal scroll while the last item is unreachable. Fix structurally with a two-row nav at ≤720 px (`flex-wrap`, brand + account on row one, `.nav-links{flex-basis:100%;order:3}` on row two with an edge fade mask) — do not shrink the font until it fits.
- **`capture_screenshot()` reuses a session path.** Two captures in one session overwrite each other; copy the file to a unique destination in the same call as the capture (`shutil.copy`) or the mobile shot is lost by the desktop shot.
- **The linter's NUMERIC_JITTER finding fires on JS source lines and CSS `text-wrap` headings.** It flags any numeric-looking line, including arithmetic, timers, and `text-wrap: balance`. Check whether the element is a live readout before editing; treat the rest as false positives documented in `references/preflight_scanner_notes.md`.
- **A `backdrop-filter` on a repeated card is a per-instance compositor layer.** Fourteen gallery cards each with `blur(10px)` cost more than the nav's single blur; replace card glass with an opaque gradient surface plus a specular top border and keep blur for chrome only.
- **A scroll-reveal that hides content by default is a blank-page bug.** Default `.reveal` to visible; only hide it under an `html.js` class, and add an independent timeout that adds `.in` to everything. A script error must not erase the page.
- **Gradient text needs a fallback.** `background-clip:text; color:transparent` erases the word when the property is unsupported and often in print; keep a solid colour outside `@supports` and restore it in `@media print`.
- **Scope the linter to the shipped surface.** It grades every `.html` it can find, so `playwright-report/`, `test-results/` and `docs/` archives contribute dozens of LOW `NUMERIC_JITTER` hits that are not your UI. Point it at the app root (or name the noise in the report). The score is not linear — clearing the single HIGH moved 46 → 56 with the same 22 LOW false positives — so never chase LOW noise to make the number look better.
- **A canvas HUD glyph needs the legibility pass, not just a tidy glyph.** Polishing pixels on a game HUD while the rule is explained only by a transient toast ships something pretty and unreadable. Run `interactive-ui-design` Step 4.7 (before/during/after surfaces, smallest-cell check) before declaring the HUD done; that skill owns the game-HUD rules and this one owns the rendering budget.
- **A headless engine cannot prove a hover state.** Chromium there reports `(hover: hover)` and `(pointer: fine)` as false, so a forced `:hover` computes an identity transform even with no reduced-motion guard. Verify the guard by reading `animationName` / `transform` under emulated `prefers-reduced-motion`, and report the hover positive control as unverified instead of claiming the lift works.
- **A universal `* { … !important }` duration rule deletes the motion system.** A global "animation speed" multiplier such as `* { transition-duration: calc(var(--animation-speed, 1) * 0.2s) !important }` assigns a *literal* duration, so at the default multiplier every element computes 1s/0.2s and every `duration-*`, `animation: … 720ms …` and `transition: transform 90ms` in the repository becomes a lie in the source — which is exactly why the UI reads "flat and dated" while the CSS looks meticulous. CSS cannot multiply an arbitrary declared duration, so scope the override to an opt-in attribute (`html[data-animation-speed] *`) written only for non-default requests, and prove it by reading `getComputedStyle` before and after.
- **A transform on the root element is a layout change in a compositor costume.** `scale(1.05)` on the element that carries `width:100%` grows its own layout box and re-rasterises every descendant's text for the length of the animation; `overflow:hidden` clips its *children*, not its own transformed box, so the growth escapes into the document as `scrollWidth > innerWidth` with **no child element reporting overflow**. When the fit check fails and no descendant is the offender, walk *ancestors* for `transform`, and move the motion to a background-only `::before` (`inset:-4%`, `background:inherit`, `z-index:-1`) instead of clamping the scale.
- **`twMerge` does not merge across variants.** `cn(variantClasses, className)` resolves conflicting utilities by keeping the last one — but `dark:bg-destructive/60` and `bg-red-50/80` belong to different variant groups, so both survive and the host's OS colour-scheme preference beats an explicit light surface inside a light panel. A surface override on a `destructive`/`default` variant must repeat itself under every variant that ships (`dark:bg-…`, `hover:bg-…`); verify with `matchMedia('(prefers-color-scheme: dark)').matches` and a computed-style read, not by eye.
- **In 3D, the scene graph is the immutable contract.** Object names, hierarchy, `userData`, animation clips and asset URLs are logic — only materials, lights, tone mapping, post-processing, camera and renderer settings are the mutable skin.
- **sRGB vs linear is a correctness bug, not a taste call.** Marking an albedo texture as linear (or a normal/ORM map as sRGB) washes out the render. Colour maps are sRGB; data maps are linear.
- **Tone mapping must happen exactly once.** With `EffectComposer`, `OutputPass` must be last; adding a manual sRGB pass on top double-converts.
- **`material.dispose()` does not free textures.** Textures are separate GPU resources; a scene that swaps models without disposing textures grows VRAM until the tab dies.
- **A `GLTFLoader` without a decoder is not "compressed".** Without Draco/meshopt/KTX2 the payload is 3-10x larger and the first load stalls.
- **`InstancedMesh` culls against the base geometry's bounds.** Scattered instances vanish unless you `computeBoundingSphere()` or disable frustum culling.
- **Negative scale on a node flips normals and tangents** — the asset renders inside-out.
- **Do not bake lighting into albedo.** Bake AO; let the runtime light the scene, or the asset only looks right under the author's light.
- **Console warnings during scene setup are defects, not noise.** `PCFSoftShadowMap` was removed in three r186 — the constant still exists, so the mistake is silent apart from a warning that gets scrolled past. Read the console.
- **Verify the API against the installed version.** `three` renames things between releases (`BatchedMesh`'s first constructor argument changed in r166). Pin `THREE.REVISION` and check the installed package before copying a snippet.
- **Swapping a `.glb` during a polish pass is implementation work, not styling.** A "prettier" asset changes triangles, VRAM and draw calls. Run the asset auditor and record the delta.
- **Marching cubes allocates its whole grid and its whole vertex buffer up front.** `maxPolyCount` sizes the buffer, not the output — two metaballs can reserve 100 000 triangles of VRAM.


## Verification

Run the linter in gate mode and confirm zero HIGH findings:

```bash
python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_visual_lint.py" . --fail-on high
echo "exit=$?"   # 0 = clean, 1 = at least one HIGH defect
```

### Runtime verification recipe (web)

The static linter cannot see viewport fit, pointer class, or motion preference. Drive the real page:

```python
# 390 px touch viewport
cdp("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
cdp("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
goto_url("http://127.0.0.1:PORT/?after=1"); wait_for_load()
assert js("document.documentElement.scrollWidth") == js("innerWidth")
assert js("Math.round(document.querySelectorAll('.nav-links a')[3].getBoundingClientRect().right)") <= 390
assert js("getComputedStyle(document.querySelector('.vote-btn')).minHeight") == "44px"

# reduced-motion contract
cdp("Emulation.setEmulatedMedia", features=[{"name":"prefers-reduced-motion","value":"reduce"}])
assert js("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
assert js("getComputedStyle(document.querySelector('.bubble')).animationName") == "none"
cdp("Emulation.setEmulatedMedia", features=[])
```

Capture desktop + mobile screenshots and inspect both with `vision_analyze`; copy each capture to a unique path in the same call (the harness reuses one output path per session).

Then walk the Phase 4 checklist above; every box must be checked with a `file_path:line` reference, not from memory.

**For 3D targets, add the asset gates:**

```bash
npx @gltf-transform/cli validate path/to/asset.glb   # asset validity
```

…and read the runtime counters straight out of the renderer (`renderer.info.render` for
draw calls / triangles, `renderer.info.memory` for leak detection) against the tier budgets
in §2.1. A screenshot rendered with `renderer.domElement.toDataURL()` immediately after
`renderer.render()` is the proof-of-work image; check it at `16:9`, `4:3`, and `9:16`.
