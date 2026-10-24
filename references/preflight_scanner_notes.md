# Preflight Scanner Notes — False Positives & Verification Rules

The `preflight_visual_lint.py` scanner is a regex-based static checker. It produces false positives that must be manually triaged — never treat every LOW as a real defect.

## Common False Positives

- **NUMERIC_JITTER_HAZARD on `timer` / `telemetry` / `metric` strings in CSS variable names or JS identifiers.** The regex matches the word, not an actual unstyled number output. Verify: does the target element actually render a changing numeric value? If it's a variable name (`--text-telemetry`) or a timer variable (`autosaveTimer`), ignore.
- **NUMERIC_JITTER_HAZARD on shader code with `float` arithmetic** (e.g., `TARGET_FRAME_MS`, `iTime`). No `font-variant-numeric` applies to GLSL uniforms. Ignore.
- **LAYOUT_THRASHING_ANIMATION** on legitimate composited transforms (`transform`, `opacity`, `border-color`) — the regex over-matches. Confirm the property being animated is `width`, `height`, `top`, `left`, `margin`, or `padding` before treating as HIGH.

## Verification Workflow

1. Run `python3 .../preflight_visual_lint.py .` after any change.
2. Filter results by `code`. Ignore all LOW hits that match the false-positive patterns above.
3. For any HIGH or non-obvious MEDIUM, open `file_path:line_range` and confirm the exact property being animated.
4. Confirm `font-variant-numeric: tabular-nums` is applied to every real telemetry readout (`#entity-count`, `.prop-row output`, `#bottom-strip`, coordinate strings, timer displays).
5. Confirm no `width`/`height`/`top`/`left`/`margin`/`padding` appears inside any `transition` or `animation` declaration.

## Reduced-Motion Guard Check
Always verify `@media (prefers-reduced-motion: reduce)` exists and collapses spatial translations to `0.01ms` while preserving functional indicators (spinners at reduced speed).
