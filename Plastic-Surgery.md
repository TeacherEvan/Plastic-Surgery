# Plastic Surgery: Autonomous UI, GUI & Dashboard Visual Maximizer

> **Canonical Skill Entrypoint**: See [`SKILL.md`](./SKILL.md) for the active Hermes / Antigravity / OpenCode skill specification.

Perform a high-precision cosmetic and rendering overhaul ("Plastic Surgery") on any new or existing UI, GUI, or dashboard. Maximize visual appeal, tactile button physics, animation smoothness, and GPU rendering efficiency while preserving **100% of underlying business logic, state bindings, and functional contracts**.

---

## 1. Core Mandate: Zero Functional Regression

When operating on an existing codebase, enforce a strict separation between **Visual Skin / Presentation (Mutable)** and **Core Logic / State (Immutable)**:

1. **Preserve All Functional Bindings**: Never delete, rename, or break event handlers (`onClick`, `onSubmit`, signal connections, IPC channels, Godot/Unity callbacks), state hooks, form `name` attributes, accessibility attributes (`aria-*`, `role`), or test selectors (`id`, `data-testid`, `data-cy`).
2. **Preserve Data Contracts**: Never alter API payload shapes, database queries, store schemas, or component prop interfaces unless strictly adding optional visual-only props (`variant`, `size`, `isLoading`).
3. **Isolate Visual Layers**: Encapsulate shaders, particle loops, spring solvers, and styling tokens in dedicated presentation modules or CSS layers (`@layer tokens, base, components, utilities`) so they never pollute domain logic.

---

## 2. Measurable Engineering Budgets

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

## 3. The 5-Phase Overhaul Pipeline

1. **Alignment Gate (Phase 0)**: Verify three core axes before writing code:
   - **Mobile vs. Desktop vs. Hybrid**
   - **Private vs. Commercial**
   - **Adult vs. All audiences**
   *(If any axis is unverifiable, halt and query the user with the 3 canonical alignment questions).*
2. **Investigate (Phase 1)**: Map workspace theme to 3–5 modern techniques (OKLCH elevation, specular borders, anti-banding dither, sub-stepped springs, tabular telemetry) and run `scripts/preflight_visual_lint.py`.
3. **Plan (Phase 2)**: Generate the formal Plastic Surgery Blueprint with locked tokens, 6-state button specs, and preserved bindings table.
4. **Implement (Phase 3)**: Apply presentation-only changes in isolated stylesheets or render passes.
5. **Verify (Phase 4)**: Audit against the post-op checklist (0 CLS, 0 numeric jitter, reduced-motion compatibility, compositor-clean CSS).

---

## 4. Reference Implementations

- **Tactile Surfaces & Buttons**: See [`references/tactile_tokens_and_surfaces.md`](./references/tactile_tokens_and_surfaces.md) for full OKLCH color token scales, specular top highlights, and complete 6-state button CSS.
- **Kinetic Physics & Math**: See [`references/kinetic_physics_and_springs.md`](./references/kinetic_physics_and_springs.md) for `expDecay`, dynamic sub-stepped spring solvers, and analytical damped harmonic oscillators.
- **Static Telemetry Scanner**: Run `python3 scripts/preflight_visual_lint.py <repo>` to audit visual and compositor performance.
