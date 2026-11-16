# Kinetic Physics, Spring Mechanics & Frame Budgets

Jittery transitions and frame-rate-dependent animations break the tactile illusion of software. This reference provides mathematically verified kinetic models, dynamic sub-stepped spring integrators, analytical harmonic oscillators, and multi-stack frame budget profiling guidelines.

---

## 1. Frame-Rate Independent Exponential Decay

A common anti-pattern in UI animation loops is fixed per-frame lerping:

```typescript
// ANTI-PATTERN: Runs 2x faster at 120Hz than at 60Hz; hitches on frame drops!
current += (target - current) * 0.1;
```

The mathematically exact, frame-rate independent solution is exponential decay governed by decay coefficient $\lambda$:

$$y(t) = y_{\text{target}} + (y_0 - y_{\text{target}}) \cdot e^{-\lambda \cdot \Delta t}$$

### Proof of Unconditional Stability

For any positive decay constant $\lambda > 0$ and any forward elapsed time $\Delta t \ge 0$, the multiplier $e^{-\lambda \Delta t} \in (0, 1]$. Because the decay multiplier never becomes negative or exceeds $1$, **exact exponential decay cannot overshoot or oscillate**, regardless of whether $\Delta t$ is $0.008\text{s}$ or $10.0\text{s}$.

Artificial upper clamping of `expDecay` itself (such as `dt <= 0.1`) is unnecessary because exponential decay is unconditionally stable (`expDecay` converges smoothly even across tab pauses). Delta time in `expDecay` only needs clamping against negative values (`Math.max(dt, 0)`):

```typescript
/**
 * Exponential decay toward target value, invariant across 60Hz, 120Hz, and variable refresh displays.
 * @param current Current value
 * @param target Goal value
 * @param decay Decay velocity constant (typically 12 - 24 for UI transitions)
 * @param dt Delta time in seconds since previous frame
 */
export function expDecay(current: number, target: number, decay = 18, dt: number): number {
  const safeDt = Math.max(dt, 0); // Only clamp against negative clock steps
  return target + (current - target) * Math.exp(-decay * safeDt);
}
```

### Converting legacy per-frame code

A per-frame retention factor `p` (where `value = target + (value - target) * p`, or `p = 1 - k` for `value += (target - value) * k`) at 60 fps converts exactly: `λ = −ln(p) × 60`.

| Old per-frame retention `p` (or blend `k`) | `λ` per second | Typical effect |
| :--- | :--- | :--- |
| `p = 0.98` (`k = 0.02`) | `1.21` | background hue following a score |
| `p = 0.964` (`k = 0.036`) | `2.19` | slow easing tail |
| `p = 0.92` (`k = 0.08`) | `5.00` | screen pulse |
| `p = 0.90` (`k = 0.10`) | `6.32` | shake decay / UI follow |
| `p = 0.50` (`k = 0.50`) | `41.6` | snappy UI state |

Call `expDecay(value, target, λ, dtSeconds)` with the delta the loop already computes.
Matching `λ` keeps the existing feel at 60 Hz and removes the 120 Hz speed-up. A loop
with several ad-hoc multipliers must convert all of them, or the one left behind still
drifts on a high-refresh display.

---

## 2. Spring Physics: Dynamic Sub-Stepping & Analytical Solutions

### The Instability Horizon of Euler Integration

Standard single-step Euler integration ($\text{vel} \mathrel{+}= a \cdot dt; \text{pos} \mathrel{+}= \text{vel} \cdot dt$) becomes unstable when $\omega_0 \cdot \Delta t > 1.0$. For an energetic UI spring with stiffness $k = 350$, natural frequency $\omega_0 = \sqrt{350} \approx 18.7\text{ rad/s}$. If a frame drops to 20 FPS ($\Delta t = 0.05\text{s}$), $\omega_0 \cdot \Delta t \approx 0.94$, approaching the threshold for divergence or violent overshoot.

Fixed 4-step divisions are insufficient during large delta-times (e.g. $0.1\text{s} / 4 = 0.025\text{s} > 0.016\text{s}$).

### Solution A: Dynamic Sub-Stepped Symplectic Euler (Fast, High Dynamic Range)

Clamp **elapsed frame time** (`MAX_FRAME_DT = 0.1`, a 10 fps floor) rather than capping the sub-step count, then sub-step dynamically based on $\Delta t_{\text{sub}} \le 0.00833\text{s}$ (120 Hz precision ceiling). Capping the step count instead lets `subDt` grow past the explicit-Euler stability bound ($h < 2 / \omega \approx 0.107\text{s}$ at default stiffness) after a tab switch or debugger pause, causing the integrator to diverge:

```typescript
export interface SpringState {
  pos: number;
  vel: number;
}

/**
 * Dynamically sub-stepped Symplectic Euler spring solver.
 * @param state Current position and velocity
 * @param target Target destination
 * @param stiffness Spring tension (default 350)
 * @param damping Spring friction (default 28 for critical damping)
 * @param dt Delta time in seconds
 */
export function stepSpringSubstepped(
  state: SpringState,
  target: number,
  stiffness = 350,
  damping = 28,
  dt = 1 / 60
): SpringState {
  let { pos, vel } = state;
  // Clamp elapsed time, NOT the step count, so subDt never exceeds 8.33ms.
  const MAX_FRAME_DT = 0.1; // 10 fps floor; beyond this the frame is a resume, not a frame
  const safeDt = Math.min(Math.max(dt, 0), MAX_FRAME_DT);

  // Guarantee subDt <= 8.33ms (120Hz precision) under any frame rate
  const MAX_SUB_DT = 0.00833;
  const steps = Math.max(1, Math.ceil(safeDt / MAX_SUB_DT));
  const subDt = safeDt / steps;

  for (let i = 0; i < steps; i++) {
    const accel = -stiffness * (pos - target) - damping * vel;
    vel += accel * subDt;
    pos += vel * subDt;
  }

  // Snap to target if settling within perceptual sub-pixel threshold
  if (Math.abs(pos - target) < 0.001 && Math.abs(vel) < 0.005) {
    return { pos: target, vel: 0 };
  }

  return { pos, vel };
}
```

### Solution B: Exact Analytical Damped Oscillator (Zero-Drift, Closed-Form)

For critical damping ($\zeta = 1$, where $\text{damping} = 2\sqrt{\text{stiffness}}$), the exact differential equation solution has **zero numerical integration error** regardless of how large $\Delta t$ is.

Expose `isAtRest()` and velocity inspectability so `requestAnimationFrame` loops can terminate reliably:

```typescript
export interface SpringSnapshot {
  pos: number;
  vel: number;
  isAtRest: boolean;
}

export class AnalyticalSpring {
  public pos: number;
  public vel: number;
  public target: number;
  private omega: number; // Angular frequency sqrt(k)

  constructor(initial = 0, stiffness = 350) {
    this.pos = initial;
    this.vel = 0;
    this.target = initial;
    this.omega = Math.sqrt(stiffness);
  }

  setTarget(target: number) {
    this.target = target;
  }

  isAtRest(posTolerance = 0.001, velTolerance = 0.005): boolean {
    return Math.abs(this.pos - this.target) <= posTolerance && Math.abs(this.vel) <= velTolerance;
  }

  update(dt: number): SpringSnapshot {
    const safeDt = Math.max(dt, 0); // No upper clamp: exact math converges smoothly over any duration
    const x0 = this.pos - this.target;
    const v0 = this.vel;
    const decay = Math.exp(-this.omega * safeDt);

    // Exact closed-form solution: x(t) = (c1 + c2*t) * exp(-omega*t)
    const c1 = x0;
    const c2 = v0 + this.omega * x0;

    const nextX = (c1 + c2 * safeDt) * decay;
    this.vel = (c2 - this.omega * (c1 + c2 * safeDt)) * decay;
    this.pos = this.target + nextX;

    if (this.isAtRest()) {
      this.pos = this.target;
      this.vel = 0;
    }

    return {
      pos: this.pos,
      vel: this.vel,
      isAtRest: this.isAtRest()
    };
  }
}
```

---

## 3. Measurable Engineering Budgets & Latency Ceilings

To keep UI at 60 FPS or 120 FPS high-refresh rates, adhere to these hard budgets:

| Stage | 60 Hz Budget | 120 Hz Budget | Primary Culprit / Diagnostic |
| :--- | :--- | :--- | :--- |
| **Input-to-Photon** | $\le 16.0\text{ ms}$ | $\le 8.33\text{ ms}$ | Laggy active CSS transitions (`>30ms`), synthetic event queues |
| **JS / Engine Update** | $\le 10.0\text{ ms}$ | $\le 5.0\text{ ms}$ | Heap allocations inside `requestAnimationFrame`, unthrottled resize/scroll |
| **DOM Style / Layout** | $\le 2.0\text{ ms}$ | $\le 1.0\text{ ms}$ | Layout thrashing (reading `getBoundingClientRect` then writing style) |
| **GPU Composite / Paint** | $\le 4.0\text{ ms}$ | $\le 2.33\text{ ms}$ | Excessive `backdrop-filter: blur()`, un-promoted moving layers |
| **Cumulative Layout Shift** | `0.00` | `0.00` | Unreserved dimensions on dynamic counters, skeleton cards, or images |

---

## 4. Multi-Stack Rendering Rules

### Web DOM & Canvas

- **DPR Clamping**: Always clamp device pixel ratio between `1.0` and `2.0` (`Math.min(window.devicePixelRatio || 1, 2.0)`). 3x/4x mobile viewports cause fill-rate collapse.
- **Off-Screen Pause**: Wrap `requestAnimationFrame` loops in `IntersectionObserver` or pause when `document.hidden === true`.

### Pygame / Python GUI

- Pre-render static font strings into a cached dictionary during init/resize. Calling `font.render()` inside `draw()` allocates new Python heap objects every single frame.
- Batch rectangular blits via `pygame.Surface.blits()`.

### Godot & Unity

- Use UI Canvas / Control nodes with anchors locked.
- Avoid animating `size` or `custom_minimum_size` in tweens; animate `scale` or `modulate` to keep compositor updates off the CPU layout pass.

---

## 5. Keeping Per-Frame State Out of the Reconciler

`expDecay` and the spring solvers above assume the loop can mutate numbers freely. In a component framework that assumption breaks silently: if position lives in framework state, every tick produces a new object, the reconciler diffs every node, and each node's `style` attribute is rewritten — so the animation runs at frame rate *through the reconciler*, which is the most expensive possible transport.

**The split.** Membership belongs in state; position belongs to the frame clock.

```typescript
// State: `{ id, emoji, speed, lane, x, y }` where x/y are SPAWN values only.
// A movement-only frame must produce NO new array so the framework bails out.
setObjects((prev) => (fallenIds.length ? prev.filter((o) => !fallen.has(o.id)) : prev));
//                ^ returning `prev` unchanged is the entire optimisation
```

```typescript
// Positions: a mutable map advanced in place, never rendered.
advancePositions(objects, positions, screenHeight, speedMultiplier); // returns fallenIds only
```

**The writer.** Each element registers its node once on mount; the loop writes to it directly.

```typescript
const nodes = new Map<string, HTMLElement>();
const lastX = new Map<string, number>();

export const registerObjectNode = (id: string, node: HTMLElement | null) => {
  if (node) nodes.set(id, node);
  else { nodes.delete(id); lastX.delete(id); }   // ref callbacks fire with null first
};

export const writeFrames = (objects, positions) => {
  for (const o of objects) {
    const el = nodes.get(o.id), p = positions.get(o.id);
    if (!el || !p) continue;
    // LAYOUT property: assign only when it changes. Re-assigning an identical
    // value still invalidates layout.
    if (lastX.get(o.id) !== p.x) { el.style.left = `${p.x}%`; lastX.set(o.id, p.x); }
    el.style.transform = `translate3d(-50%, ${p.y}px, 0)`;   // compositor-only
  }
};
```

Rules that keep the split honest:

- **Write layout properties only on change; write `transform`/`opacity` every frame.** `left`, `top`, `width`, `height`, `margin` and `padding` trigger layout on assignment even when the value is unchanged. Animating `left` at 60 Hz is a layout pass per frame that no amount of framework tuning will fix.
- **Gate the dispatch, not the work.** Compute first, then dispatch only if membership changed (`if (survivors !== roster) setObjects(survivors)`). A dispatch that always returns the same value still enters the reconciler.
- **Keep side effects out of the state updater.** React and similar frameworks may invoke an updater more than once for one commit, so telemetry inside it double-counts. Advance and report outside; use the updater only to prune.
- **Audit every reader after the move.** Anything that used to read `object.x` now reads the spawn value forever. Collision, culling and telemetry must all be repointed at the live map — a stale reader is a silent behaviour bug, not a perf regression.
- **Prove it with counts, not fps.** Assert "a movement-only frame dispatches nothing" and "`left` is not rewritten while x is stable" as unit tests; see `surgical-audit` → `references/runtime-probe-harness.md` §8e for why wall-clock timing is the wrong instrument.
