---
name: plastic-surgery
description: Execute a precision UI/GUI/Dashboard visual overhaul ("Plastic Surgery") that maximizes visual appeal, tactile buttons, animations, rendering smoothness, and workspace-themed modern techniques using a strict Alignment Gate -> Collaboration State -> Investigate -> Plan -> Implement -> Verify workflow without breaking business logic.
---
# Plastic-surgery.md — Autonomous UI, GUI & Dashboard Visual Maximizer

Perform a high-precision cosmetic and rendering overhaul ("Plastic Surgery") on any new or existing UI, GUI, or dashboard. Maximize visual appeal, tactile button physics, animation smoothness, and GPU rendering efficiency while preserving **100% of underlying business logic, state bindings, and functional contracts**.

---

## 1. Core Surgical Mandate: Zero Functional Regression

When operating on an existing codebase, enforce a strict separation between **Visual Skin / Presentation (Mutable)** and **Core Logic / State (Immutable)**:

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
4. **Take It From There (Adaptive Follow-Up)**:
   - Once the user answers the initial three questions, synthesize their constraints and ask at most **1 to 2 targeted follow-up questions** if specific aesthetic polarity (e.g., dark-first obsidian vs. daylight editorial, shader intensity, or information density) needs lock-in.
   - Once aligned, proceed immediately to **Phase 1 (Investigate)**.

---

### Phase 1: Investigate Modern & Popular Techniques for the Workspace Theme

With alignment locked, actively investigate modern, high-craft visual techniques tailored specifically to the **workspace theme** and **rendering stack**:

1. **Theme-Specific Technique Research**:
   - Map the workspace's core theme (e.g., *Autonomous AI Agent / Server Telemetry*, *Payroll / Fintech Ledger*, *Early-Childhood Educational Game*, *Brutalist Megastructure 3D Environment*, *Robotics / Hardware Synth Controller*) to cutting-edge UI/GUI patterns in that vertical.
   - Select **3 to 5 modern techniques** that maximize visual appeal for that exact theme:
     - **Surface & Depth Engineering:** Perceptual `oklch()` surface elevation steps (`+3%` lightness per z-layer), `1px` top-edge specular borders (`inset 0 1px 0 oklch(1 0 0 / 0.14)`), `1.5%` SVG `fractalNoise` anti-banding dither, cursor-tracked radial spotlights, or recessed OLED/LCD bevels.
     - **Tactile & Kinetic Motion:** Critically damped spring physics (`stiffness: 350, damping: 28`), frame-rate independent exponential decay (`lerp(cur, target, 1 - exp(-decay * dt))`), FLIP layout transitions, or staggered entrance choreography (`15-25 ms` per item, capped at `250 ms` total).
     - **Dashboard & Telemetry Craft:** `font-variant-numeric: tabular-nums` locked numeric columns, canvas-backed 60 FPS micro-sparklines, glowing semantic status pips (`0 0 8px var(--status-nominal)`), and tactile keycap shortcut hints (`kbd`).
2. **Pre-Op Visual Defect Audit**:
   - Catalog every visual flaw in the current UI with exact `file_path:line_range` references: dead/flat buttons lacking active depression, un-eased state snaps, layout-thrashing CSS/GUI properties, numeric jitter on live counters, grid blowout (`min-width: auto`), or un-cached per-frame font/surface allocations in game loops.

---

### Phase 2: Plan the Visual Overhaul

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
| `--surface-canvas` | `oklch(...)` | Base background void / canvas |
| `--surface-card` | `oklch(...)` | Elevated container + `1px` specular top border |
| `--surface-interactive` | `oklch(...)` | Button / control resting surface |
| `--accent-primary` | `oklch(...)` | Primary action & focus ring (`>= 4.5:1` AA) |
| `--text-telemetry` | `oklch(...)` | High-priority readouts (`>= 7.0:1` AAA, `tabular-nums`) |

## 3. Six-State Tactile Button & Control Specification
- **Default:** [Base gradient, `1px` top specular highlight, dual ambient + key shadow]
- **Hover (`@media (hover: hover)`):** [`140ms cubic-bezier(0.22, 1, 0.36, 1)`, `translate3d(0, -1px, 0)`, border luminance lift]
- **Active / Pressed:** [`<= 16ms` (`30ms` transition), `translate3d(0, 1px, 0) scale(0.982)`, inset shadow inversion]
- **Focus-Visible:** [`2px solid var(--accent-primary)`, `2px` offset ring]
- **Loading:** [Width-locked bounding box, inline spinner/shimmer, `pointer-events: none`]
- **Disabled:** [`opacity: 0.45`, desaturated fill, `cursor: not-allowed`]

## 4. Rendering & Smoothness Execution Plan
- **DOM / Layout:** [Compositor-only transforms, `minmax(0, 1fr)` grid locks, `0fr -> 1fr` row transitions]
- **Canvas / GUI / Game Loop:** [DPR clamp `[1, 2]`, `dt` exponential decay, cached text/surface blitting, off-screen pause guards]
- **Preserved Bindings Check:** [List of IDs, `data-testid`s, hooks, and callbacks guaranteed untouched]
```

---

### Phase 3: Implement the Overhaul (Web, Desktop GUI & Game Stacks)

Apply the planned changes cleanly and modularly across the target stack:

#### A. Six-State Tactile Button Blueprint (Web / CSS)
```css
.btn-surgical {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 40px; /* Set to 44px on mobile/touch viewports */
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: var(--font-sm, 0.875rem);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary, oklch(0.96 0.005 265));
  background: linear-gradient(180deg, oklch(0.25 0.02 265) 0%, oklch(0.19 0.02 265) 100%);
  border: 1px solid oklch(1 0 0 / 0.12);
  box-shadow:
    inset 0 1px 0 0 oklch(1 0 0 / 0.14),
    0 1px 2px 0 oklch(0 0 0 / 0.45),
    0 4px 8px -2px oklch(0 0 0 / 0.25);
  transform: translate3d(0, 0, 0) scale(1);
  transition:
    transform 140ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 140ms cubic-bezier(0.22, 1, 0.36, 1),
    border-color 140ms cubic-bezier(0.22, 1, 0.36, 1),
    background 140ms cubic-bezier(0.22, 1, 0.36, 1);
  user-select: none;
  touch-action: manipulation;
  cursor: pointer;
}

@media (hover: hover) and (pointer: fine) {
  .btn-surgical:hover:not(:disabled) {
    border-color: oklch(1 0 0 / 0.24);
    transform: translate3d(0, -1px, 0) scale(1.005);
    box-shadow:
      inset 0 1px 0 0 oklch(1 0 0 / 0.22),
      0 4px 12px -2px oklch(0 0 0 / 0.5),
      0 0 16px -4px oklch(0.68 0.19 260 / 0.3);
  }
}

.btn-surgical:active:not(:disabled) {
  transition-duration: 25ms;
  transform: translate3d(0, 1px, 0) scale(0.982);
  box-shadow: inset 0 2px 4px 0 oklch(0 0 0 / 0.65);
}

.btn-surgical:focus-visible {
  outline: 2px solid oklch(0.68 0.19 260);
  outline-offset: 2px;
}

.btn-surgical:disabled,
.btn-surgical[data-loading="true"] {
  opacity: 0.45;
  pointer-events: none;
}
```

#### B. Frame-Rate Independent Smoothness (Canvas / Pygame / Godot / Unity / JS Loops)
Never use fixed per-frame multipliers (`val += (target - val) * 0.1`), which double animation speed at 120 Hz compared to 60 Hz. Always use delta-time (`dt` in seconds) exponential decay or clamped spring integration:

```typescript
// 1. Frame-Rate Independent Exponential Decay (60Hz / 120Hz / Variable Refresh Safe)
export function expDecay(current: number, target: number, decay = 18, dt: number): number {
  const safeDt = Math.min(Math.max(dt, 0), 0.1); // Clamp tab-switch dt spikes
  return target + (current - target) * Math.exp(-decay * safeDt);
}

// 2. Critically Damped Spring Step (Stiffness 350, Damping 28)
export function stepSpring(
  pos: number,
  vel: number,
  target: number,
  stiffness = 350,
  damping = 28,
  dt = 1 / 60
): [number, number] {
  const safeDt = Math.min(Math.max(dt, 0), 0.064);
  const accel = -stiffness * (pos - target) - damping * vel;
  const nextVel = vel + accel * safeDt;
  const nextPos = pos + nextVel * safeDt;
  return [nextPos, nextVel];
}
```

#### C. Native / Desktop / Python GUI Smoothness Rules (Pygame, Qt/PySide, Tkinter, Godot)
- **Zero Per-Frame Font/Surface Instantiation**: Pre-render static labels, 9-slice button states (`default`, `hover`, `pressed`, `disabled`), and drop-shadow surfaces during initialization or resize—never inside `draw()` / `paintEvent()` / `_process()`.
- **Dirty-Rect & Batching**: Group UI draw calls into a single texture atlas or `Surface.blits()` batch to keep render pass duration under `3.33 ms`.
- **Sub-Pixel Jitter Prevention**: Store animated UI coordinates as `float` for spring/decay math, but snap to `Math.round()` / `int()` at final text/border rasterization if the renderer lacks sub-pixel anti-aliasing.

---

### Phase 4: Post-Op Verification Checklist

Before concluding the task, verify every item below:

- [ ] **Alignment Verified**: All 3 axes (*Mobile/Desktop*, *Private/Commercial*, *Adult/All audiences*) were either proven from the codebase or confirmed via the Collaboration State.
- [ ] **Functional Integrity**: Zero broken callbacks, state hooks, props, or `data-testid` / `id` selectors.
- [ ] **Compositor Clean**: Zero transitions or keyframes animating `width`, `height`, `top`, `left`, `margin`, or `padding`.
- [ ] **VRAM & Overdraw Safe**: No static `will-change` on repeating nodes; maximum `2` overlapping `backdrop-filter: blur()` layers (`<= 16px` radius).
- [ ] **Zero Numeric Jitter**: `font-variant-numeric: tabular-nums` (or fixed-width glyph layout in native/game GUIs) applied to all live metrics, timers, and tables.
- [ ] **Reduced-Motion Guard**: `@media (prefers-reduced-motion: reduce)` or engine accessibility setting collapses spatial translations to `120 ms` opacity fades.
