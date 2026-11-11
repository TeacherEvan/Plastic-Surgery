# Plastic-Surgery

**UI / GUI / Dashboard / 3D Visual Overhaul** — the visual counterpart to `surgical-implementation`.

Plastic Surgery is a high-craft agent skill for **Nous Hermes Agent**, **Google Antigravity**, **OpenCode**, and **Cursor** that performs precision cosmetic and rendering overhauls on UI, GUI, dashboards, and **Three.js/WebGL scenes**: tactile buttons, perceptual `oklch()` colour tokens, sub-stepped spring physics, compositor-clean animations, workspace-themed design, and budgeted 3D asset pipelines — while guaranteeing **100% functional regression safety**.

---

## Files & Repository Architecture

| File | Purpose |
|---|---|
| `SKILL.md` | Core skill manifest + 5-phase overhaul pipeline (Alignment -> Investigate -> Plan -> Implement -> Verify) |
| `scripts/preflight_visual_lint.py` | Zero-mutation static AST & CSS scanner (detects layout thrashing, numeric jitter, blur overdraw, reduced-motion gaps, and Three.js `THREE_*` 3D hazards) |
| `scripts/preflight_gltf_budget.py` | Zero-mutation glTF/GLB asset auditor (triangles, draw calls, texture VRAM, material slots, LOD/compression coverage, structural defects) against a device tier |

| `references/tactile_tokens_and_surfaces.md` | Perceptual `oklch()` color tokens, specular top-edge borders, OLED anti-banding dither, and 6-state tactile button specification |
| `references/kinetic_physics_and_springs.md` | Frame-rate independent `expDecay`, dynamic sub-stepped symplectic spring integrators, analytical harmonic oscillators, and frame budget tables |
| `references/threejs_3d_asset_pipeline.md` | End-to-end 3D asset creation (budget -> blockout -> UV -> PBR bake -> LOD -> glTF 2.0 -> Draco/KTX2 -> runtime), Three.js materials/lighting/post-processing, procedural geometry, instancing, and render budget tiers |
| `references/preflight_scanner_notes.md` | Known false positives of the linter (CSS variables, GLSL uniforms, timer identifiers, three.js module boundaries) and their triage rules |
| `install_plastic_surgery.sh` | One-command installer for Hermes, OpenCode, Antigravity, and Cursor |


---

## Installation

### Nous Hermes Agent (also OpenCode & Antigravity)

OpenCode's `~/.config/opencode/skills` and Antigravity's skill sync read from `~/.hermes/skills/`, so one install covers all targets:

```bash
bash install_plastic_surgery.sh
```

Or one-liner directly from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/TeacherEvan/Plastic-Surgery/main/install_plastic_surgery.sh | bash
```

### Cursor & Local Workspaces

To deploy directly to Cursor or a specific project workspace:

```bash
# Cursor global skills
mkdir -p ~/.cursor/skills/plastic-surgery
cp SKILL.md install_plastic_surgery.sh ~/.cursor/skills/plastic-surgery/
cp -r references scripts ~/.cursor/skills/plastic-surgery/

# Antigravity project-local workspace
mkdir -p .agents/skills/plastic-surgery
cp SKILL.md install_plastic_surgery.sh .agents/skills/plastic-surgery/
cp -r references scripts .agents/skills/plastic-surgery/
```

---

## Usage

1. **Invoke the Skill**: Trigger the skill in your agent session via `/plastic-surgery` or by asking for a visual overhaul: *"Make this dashboard look modern and tactile without breaking any logic."*
2. **Run Preflight Visual Linter**:
   ```bash
   python3 ~/.hermes/skills/plastic-surgery/scripts/preflight_visual_lint.py /path/to/target
   ```
3. **Audit 3D Assets (when the target ships 3D)**:
   ```bash
   python3 ~/.hermes/skills/plastic-surgery/scripts/preflight_gltf_budget.py asset.glb --tier medium --fail-on high
   ```
4. **Execute the 5-Phase Pipeline**:
   - **Phase 0: Alignment Gate** $\rightarrow$ Three axes (*Mobile/Desktop*, *Private/Commercial*, *Adult/All audiences*). Halts and asks if unaligned.
   - **Phase 1: Investigate** $\rightarrow$ Map workspace theme, select 3–5 modern techniques, run preflight lint.
   - **Phase 2: Plan** $\rightarrow$ Generate Plastic Surgery Blueprint.
   - **Phase 3: Implement** $\rightarrow$ Apply presentation-layer changes in isolated CSS/presentation modules.
   - **Phase 4: Verify** $\rightarrow$ Post-op verification (frame budgets, INP/CLS, zero numeric jitter, reduced-motion guard, 3D draw-call/triangle/VRAM budgets).
5. **Create or Polish 3D Assets**:
   - New asset $\rightarrow$ follow `references/threejs_3d_asset_pipeline.md` §2 (budget $\rightarrow$ blockout $\rightarrow$ UV $\rightarrow$ PBR bake $\rightarrow$ LOD $\rightarrow$ glTF $\rightarrow$ Draco/KTX2 $\rightarrow$ runtime audit).
   - Existing scene $\rightarrow$ apply §5–§9 (PBR materials, IBL lighting, tuned shadows, ordered post chain, budget assertions) without touching the scene graph.


---

## Skill Metadata

The frontmatter in [`SKILL.md`](./SKILL.md) is the single source of truth for `name`,
`description`, `version`, `author`, `platforms`, and `metadata.hermes`. It is deliberately
not duplicated here — a second copy is how the previous `description` and `tags` drifted
out of sync with the skill the loader actually reads.

---

## Contributing & Upstream

- Canonical repository: `https://github.com/TeacherEvan/Plastic-Surgery`
- Hermes skill mirror (repertoire): `https://github.com/TeacherEvan/hermes-skills` (`skills/plastic-surgery/`)
- Fork the canonical repo and submit a PR against `main`.
- Never edit a peer skill's files without explicit OK (per the Junto rule).
