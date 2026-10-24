---
name: plastic-surgery
description: "Use when doing a visual UI overhaul without logic drift."
version: 1.2.0
author: "TeacherEvan, Fenrie (Lea's AI wolf), Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: creative
    tags: [visual, ui-overhaul, design-system, tactile-design, accessibility, animation]
    requires_tools: [read_file, search_files, browser, vision, terminal]
    related_skills: [surgical-orchestration, surgical-implementation, surgical-audit]
---

# Plastic Surgery — Autonomous UI, GUI & Dashboard Visual Maximizer

Execute a precision **UI / GUI / Dashboard visual overhaul** ("Plastic Surgery") that maximizes visual appeal, tactile button physics, animation smoothness, and workspace-themed modern techniques using a strict **Alignment Gate -> Collaboration State -> Investigate -> Plan -> Implement -> Verify** workflow — while guaranteeing **100% zero functional regression**.

---

## When to Use

- The user says a UI looks flat, dated, cheap, or "not premium" and wants it lifted without touching behaviour.
- You need a measurable visual pass: tactile button states, motion physics, contrast, numeric jitter, reduced-motion coverage.
- A dashboard, settings surface, or game HUD needs polish before a demo or release.

**Don't use for:** changing business logic, adding features, restructuring state, or fixing a functional bug — use `surgical-implementation` for that. If the complaint is "it stutters" and the cause is a hot loop rather than the visual layer, use `surgical-audit` first; this skill will happily polish a canvas that is still dropping frames.

---

## Overview & Auxiliary Resources

Plastic Surgery is the visual counterpart to `surgical-implementation`: where implementation care ensures logic is correct and robust, Plastic Surgery elevates pixels from "flat and forgettable" to "tight, tactile, and responsive". It treats the visual layer as an isolated surgical skin: the underlying functional structure (state, event bindings, API contracts, test hooks, accessibility roles) is **strictly immutable**.

### Auxiliary Skill Resources (Progressive Disclosure)
- `scripts/preflight_visual_lint.py`: Zero-mutation static scanner detecting layout-thrashing animations, un-budgeted blurs, numeric jitter, and reduced-motion gaps.
- `references/tactile_tokens_and_surfaces.md`: Perceptual `oklch()` color system, APCA/WCAG contrast proofs, specular top-edge insets, sub-perceptual OLED dithering, and 6-state tactile button specification.
- `references/kinetic_physics_and_springs.md`: Exact `expDecay()` stability proofs, dynamic sub-stepped symplectic spring integrators, analytical harmonic oscillators, and frame budget tables.
- `references/preflight_scanner_notes.md`: Known false positives of the linter (CSS variable names, GLSL uniforms, timer identifiers) and how to triage them before acting.

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
   - Map the domain vertical (*AI Telemetry*, *Fintech Ledger*, *Cyberpunk/Terminal TUI*, *Hardware Synth*, etc.) to 3–5 cutting-edge visual techniques:
     - **Surface & Depth:** `oklch()` tonal lightness elevation (`+3%` per z-layer), top-edge specular borders (`inset 0 1px 0 oklch(1 0 0 / 0.14)`), sub-perceptual $1.5\%$ SVG anti-banding dither, or OLED bezel shadows.
     - **Tactile & Kinetic Motion:** Frame-rate independent exponential decay, dynamic sub-stepped spring solvers, FLIP layout animations, and staggered entrances (`15-25 ms` stagger, max `250 ms`).
     - **Telemetry & Readouts:** `font-variant-numeric: tabular-nums` column locking, canvas micro-sparklines, glowing semantic status pips (`0 0 8px var(--status-nominal)`), and tactile keycap hints (`<kbd>`).
3. **Pre-Op Defect Catalog**:
   - Catalog all visual and kinetic bugs with `file_path:line_range` references: layout-thrashing animations, missing `:active` button depression, hover sticking on touch devices, unreserved dynamic bounds, or font allocations in draw loops.

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
- **Preserved Bindings Check:** [List of IDs, `data-testid`s, hooks, and callbacks guaranteed untouched]
```

---

### Phase 3: Implement the Overhaul (Web, Desktop GUI & Game Stacks)

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

#### C. Native / Desktop / Python GUI Smoothness Rules (Pygame, Qt/PySide, Tkinter, Godot)
- **Zero Per-Frame Font/Surface Instantiation**: Pre-render static labels, 9-slice button states (`default`, `hover`, `pressed`, `disabled`), and drop-shadow surfaces during initialization or resize—never inside `draw()` / `paintEvent()` / `_process()`.
- **Dirty-Rect & Batching**: Group UI draw calls into a single texture atlas or `Surface.blits()` batch to keep render pass duration under `3.33 ms`.
- **Sub-Pixel Jitter Prevention**: Store animated UI coordinates as `float` for spring/decay math, but snap to `Math.round()` / `int()` at final text/border rasterization if the renderer lacks sub-pixel anti-aliasing.

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

---

## Pitfalls

- **A capped sub-step count is not stability.** Any spring integrator must clamp the *frame delta*; a `Math.min(steps, N)` guard silently grows `subDt` and diverges after a tab resume. Clamp `dt` at the loop, then sub-step as finely as needed.
- **The preflight linter only exits non-zero with `--fail-on`.** A plain run prints a score and exits 0 — a CI job wired to the bare command will always be green.
- **`backdrop-filter` cost is per-layer, not per-radius.** Two 16 px blurs stacked cost more than one 40 px blur; the linter's 16 px rule is a proxy, not a budget proof.
- **`pointer: coarse` is not the same as "mobile".** Hybrid laptops report a fine pointer and a touchscreen; the 44 px touch target must be driven by `any-pointer: coarse` if both matter.
- **Preserved bindings are the contract.** Renaming a `data-testid`, an `aria-*` attribute, or a form `name` is a functional regression even when the page looks perfect.
- **Do not "fix" a stutter by adding `will-change`.** A permanent compositor layer costs VRAM on every element that has it; scope it to the interaction and remove it after.
- **Contrast claims from `oklch()` have to be measured.** Convert to sRGB and compute APCA/WCAG against the actual composited background, including gradients and overlays — not the token's nominal value.

## Verification

Run the linter in gate mode and confirm zero HIGH findings:

```bash
python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/plastic-surgery}/scripts/preflight_visual_lint.py" . --fail-on high
echo "exit=$?"   # 0 = clean, 1 = at least one HIGH defect
```

Then walk the Phase 4 checklist above; every box must be checked with a `file_path:line` reference, not from memory.
