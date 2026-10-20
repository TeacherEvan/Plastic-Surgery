# Tactile Tokens & Perceptual Surface Engineering

High-craft UI, GUI, and dashboard overhauls require moving beyond flat, lifeless surfaces to physically grounded, perceptual depth. This reference provides the mathematical models, CSS/GLSL specifications, and design tokens for state-of-the-art tactile surfaces.

---

## 1. Perceptual Colour Space (`oklch`) & Contrast Rigor

Never construct color scales in sRGB or Hex for lighting calculations. sRGB is perceptually non-uniform: yellow at 50% lightness appears far brighter than blue at 50% lightness. `oklch` separates Lightness ($L \in [0, 1]$), Chroma ($C \in [0, 0.4]$), and Hue ($H \in [0, 360]$) in human perceptual coordinates.

In `oklch(L C H)`, perceptual lightness $L$ is a cube-root transfer function of CIE relative luminance ($Y \approx L^3$ for near-achromatic hues). Contrast calculations must use the physical luminance $Y$, not the raw $L$ percentage.

```css
:root {
  /* Surface Void & Canvas (Dark Obsidian Base) */
  --surface-void: oklch(0.12 0.015 265);      /* Y ≈ 0.00173 */
  --surface-canvas: oklch(0.15 0.018 265);    /* Y ≈ 0.00338 */
  
  /* Perceptual Elevation Steps (+3% lightness per z-layer) */
  --surface-layer-1: oklch(0.18 0.02 265);    /* Y ≈ 0.00583 */
  --surface-layer-2: oklch(0.21 0.022 265);   /* Y ≈ 0.00926 */
  --surface-layer-3: oklch(0.24 0.024 265);   /* Y ≈ 0.01382 */
  
  /* Specular Highlight Tokens (Physical Top-Edge Insets) */
  --specular-top-subtle: inset 0 1px 0 0 oklch(1 0 0 / 0.08);
  --specular-top-elevated: inset 0 1px 0 0 oklch(1 0 0 / 0.16);
  --specular-top-active: inset 0 1px 0 0 oklch(1 0 0 / 0.24);

  /* Primary Accent & Dedicated Foreground Pairings */
  --accent-primary: oklch(0.68 0.19 260);         /* Y ≈ 0.314 */
  --accent-primary-hover: oklch(0.72 0.20 260);   /* Y ≈ 0.373 */
  --accent-primary-active: oklch(0.64 0.18 260);  /* Y ≈ 0.262 */
  --text-on-accent: oklch(0.12 0.02 265);         /* Y ≈ 0.00173 | CR = 7.05:1 (WCAG AAA) */
  
  /* Semantic Telemetry Tokens */
  --status-nominal: oklch(0.72 0.17 145);  /* Clean Emerald */
  --status-warning: oklch(0.78 0.16 75);   /* Radiant Amber */
  --status-critical: oklch(0.65 0.22 25);  /* Precision Crimson */

  /* Text & Readout Contrast Hierarchy (Mathematically Verified against Layer-1) */
  --text-primary: oklch(0.96 0.005 265);     /* Y ≈ 0.885 | APCA -86 Lc (LC 75+ AAA) */
  --text-secondary: oklch(0.79 0.015 265);   /* Y ≈ 0.493 | APCA -66.8 Lc (LC 65+ AA) */
  --text-muted: oklch(0.66 0.02 265);        /* Y ≈ 0.287 | APCA -45.9 Lc (LC 45 UI Readout) */
  --text-telemetry: oklch(0.98 0.002 265);   /* Tabular figures, high-priority monospace */
}
```

> [!IMPORTANT]
> **Accent Contrast Rule**: When using `--accent-primary` (`oklch(0.68...)`) as a background fill, pair it strictly with `--text-on-accent: oklch(0.12 0.02 265)`. Pairing it with `--text-primary` (`oklch(0.96...)`) yields a contrast ratio of only `2.57:1`, failing both WCAG AA (`4.5:1`) and UI element guidelines (`3.0:1`).

---

## 2. Specular Top-Edge Insets & Dual-Shadow Geometry

Flat drop shadows look muddy. Physical materials reflect ambient light from above and occlude downward:

```css
/* Tactile Card / Panel Container */
.card-tactile {
  background: var(--surface-layer-1);
  border: 1px solid oklch(1 0 0 / 0.09);
  border-radius: 12px;
  box-shadow:
    var(--specular-top-subtle),
    0 1px 2px 0 oklch(0 0 0 / 0.35),
    0 8px 16px -4px oklch(0 0 0 / 0.25);
  contain: layout style;
}
```

---

## 3. Sub-Perceptual Anti-Banding Dither (OLED / LCD)

Smooth dark gradients in sRGB/8-bit suffer from noticeable banding. Apply an ultra-light $1.5\%$ dither noise layer behind foreground content.

To prevent the noise layer from rendering over child elements, enforce `isolation: isolate` on the container and place the pseudo-element at `z-index: -1`:

```html
<!-- Single inline SVG filter at root of application -->
<svg style="position: fixed; width: 0; height: 0; pointer-events: none;" aria-hidden="true">
  <filter id="dither-noise">
    <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" result="noise"/>
    <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 0.018 0"/>
    <feBlend mode="overlay" in="SourceGraphic"/>
  </filter>
</svg>
```

```css
.canvas-dithered {
  position: relative;
  isolation: isolate; /* Creates isolated local stacking context */
}

.canvas-dithered::before {
  content: "";
  position: absolute;
  inset: 0;
  filter: url("#dither-noise");
  opacity: 0.75;
  pointer-events: none;
  z-index: -1; /* Strictly behind normal-flow and positioned child elements */
}
```

---

## 4. Production-Ready Six-State Tactile Button

This implementation incorporates key compositor, accessibility, and interaction best practices:
1. **Compositor Efficiency**: Avoids permanent resting `translate3d(0, 0, 0)` layer allocation, saving VRAM on button-dense dashboards and avoiding trapped stacking contexts.
2. **Smooth Hover Interpolation**: Uses an `::after` pseudo-element with opacity transition instead of non-interpolable gradient snapping or expensive per-frame `box-shadow` repaints.
3. **Interactive Hit-Testing**: Keeps pointer events active during loading/disabled states so `cursor: not-allowed` or `cursor: wait` renders properly while intercepting duplicate clicks via standard button logic.
4. **Width-Locking**: Prevents Cumulative Layout Shift (CLS) when loading spinners appear.

```css
/* Base resting state */
.btn-tactile {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 40px;
  min-width: 80px;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
  color: var(--text-primary);
  background: linear-gradient(180deg, oklch(0.26 0.02 265) 0%, oklch(0.20 0.02 265) 100%);
  border: 1px solid oklch(1 0 0 / 0.12);
  box-shadow:
    var(--specular-top-subtle),
    0 1px 2px 0 oklch(0 0 0 / 0.45),
    0 4px 8px -2px oklch(0 0 0 / 0.25);
  /* Do not set resting translate3d(0,0,0) here: avoid permanent GPU backing store */
  user-select: none;
  touch-action: manipulation;
  cursor: pointer;
  -webkit-font-smoothing: antialiased;
  transition:
    transform 140ms cubic-bezier(0.22, 1, 0.36, 1),
    border-color 140ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* Compositor-accelerated hover glow overlay */
.btn-tactile::after {
  content: "";
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: linear-gradient(180deg, oklch(1 0 0 / 0.06) 0%, oklch(1 0 0 / 0.00) 100%);
  box-shadow:
    var(--specular-top-elevated),
    0 4px 12px -2px oklch(0 0 0 / 0.5),
    0 0 16px -4px oklch(0.68 0.19 260 / 0.35);
  opacity: 0;
  pointer-events: none;
  transition: opacity 140ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* 1. Touch viewport hit target expansion */
@media (pointer: coarse) {
  .btn-tactile {
    min-height: 44px;
    padding: 0.625rem 1.125rem;
  }
}

/* 2. Hover (Gated exclusively to fine-pointer devices) */
@media (hover: hover) and (pointer: fine) {
  .btn-tactile:hover:not(:disabled):not([aria-disabled="true"]):not([data-loading="true"]) {
    border-color: oklch(1 0 0 / 0.24);
    transform: translate3d(0, -1px, 0) scale(1.005);
  }
  .btn-tactile:hover:not(:disabled):not([aria-disabled="true"]):not([data-loading="true"])::after {
    opacity: 1;
  }
}

/* 3. Active / Pressed (Instant physical depression) */
.btn-tactile:active:not(:disabled):not([aria-disabled="true"]):not([data-loading="true"]) {
  transition-duration: 25ms;
  transform: translate3d(0, 1px, 0) scale(0.985);
  box-shadow:
    inset 0 2px 4px 0 oklch(0 0 0 / 0.65),
    0 1px 1px 0 oklch(0 0 0 / 0.3);
}
.btn-tactile:active:not(:disabled):not([aria-disabled="true"]):not([data-loading="true"])::after {
  opacity: 0;
}

/* 4. Focus-Visible (High-contrast, zero-layout-shift ring) */
.btn-tactile:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}

/* 5. Disabled State (Preserves cursor: not-allowed without swallowing hit tests) */
.btn-tactile:disabled,
.btn-tactile[aria-disabled="true"] {
  opacity: 0.45;
  cursor: not-allowed;
  filter: grayscale(40%);
  box-shadow: none;
  transform: none !important;
  /* Retain pointer events so cursor: not-allowed renders and tooltip wrappers work */
}

/* 6. Loading State (Width-locked bounding box to prevent CLS) */
.btn-tactile[data-loading="true"] {
  cursor: wait;
}

.btn-tactile[data-loading="true"] .btn-label {
  visibility: hidden; /* Preserves exact text width, preventing CLS */
}

.btn-tactile .btn-spinner {
  display: none;
  position: absolute;
  width: 1rem;
  height: 1rem;
  border: 2px solid oklch(1 0 0 / 0.2);
  border-top-color: var(--text-primary);
  border-radius: 50%;
  animation: btn-spin 600ms linear infinite;
}

.btn-tactile[data-loading="true"] .btn-spinner {
  display: block;
}

@keyframes btn-spin {
  to { transform: rotate(360deg); }
}

/* Accessibility: Reduced-Motion Guard */
@media (prefers-reduced-motion: reduce) {
  .btn-tactile,
  .btn-tactile::after {
    transition-duration: 0.01ms !important;
    transform: none !important;
  }
  /* Allow spinner to maintain gentle rotation for functional status awareness */
  .btn-tactile .btn-spinner {
    animation-duration: 1.5s;
  }
}
```
