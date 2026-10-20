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

Artificial upper clamping (such as `dt <= 0.1`) is an anti-pattern that freezes animations mid-air when users switch browser tabs. Delta time should only be clamped against negative values (`Math.max(dt, 0)`):

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

---

## 2. Spring Physics: Dynamic Sub-Stepping & Analytical Solutions

### The Instability Horizon of Euler Integration
Standard single-step Euler integration ($\text{vel} \mathrel{+}= a \cdot dt; \text{pos} \mathrel{+}= \text{vel} \cdot dt$) becomes unstable when $\omega_0 \cdot \Delta t > 1.0$. For an energetic UI spring with stiffness $k = 350$, natural frequency $\omega_0 = \sqrt{350} \approx 18.7\text{ rad/s}$. If a frame drops to 20 FPS ($\Delta t = 0.05\text{s}$), $\omega_0 \cdot \Delta t \approx 0.94$, approaching the threshold for divergence or violent overshoot.

Fixed 4-step divisions are insufficient during large delta-times (e.g. $0.1\text{s} / 4 = 0.025\text{s} > 0.016\text{s}$).

### Solution A: Dynamic Sub-Stepped Symplectic Euler (Fast, High Dynamic Range)

Compute dynamic sub-steps based on a maximum sub-step ceiling ($\Delta t_{\text{sub}} \le 0.00833\text{s}$, matching a 120 Hz frame budget), with an upper iteration cap (e.g., 24 steps) to avoid CPU spirals during debugger pauses:

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
  const safeDt = Math.max(dt, 0);
  
  // Guarantee subDt <= 8.33ms (120Hz precision) under any frame rate
  const MAX_SUB_DT = 0.00833;
  const steps = Math.max(1, Math.min(Math.ceil(safeDt / MAX_SUB_DT), 24));
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
