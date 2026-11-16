# Plastic-Surgery

**UI / GUI / Dashboard / 3D Visual Overhaul** — the visual counterpart to `surgical-implementation`.

Plastic Surgery is an agent skill for **Nous Hermes Agent**, **Google Antigravity**, **OpenCode**, **Cursor**, **GitHub Copilot**, and **Agents** runtimes that performs precision cosmetic and rendering overhauls on UI, GUI, dashboards, and **Three.js/WebGL scenes**: tactile buttons, sRGB-verified `oklch()` colour tokens, sub-stepped spring physics, compositor-clean animations, WCAG 2.2 checks, and budgeted 3D asset pipelines — while guaranteeing **100% functional regression safety**.

---

## Files & Repository Architecture

| File | Purpose |
| :--- | :--- |
| [SKILL.md](./SKILL.md) | Core skill manifest + 5-phase overhaul pipeline (Alignment -> Investigate -> Plan -> Implement -> Verify) |
| [AGENTS.md](./AGENTS.md) | Agent instructions, isolated test/lint commands, and source-of-truth sync rules |
| [LICENSE](./LICENSE) | MIT license |
| [scripts/preflight_visual_lint.py](./scripts/preflight_visual_lint.py) | Zero-mutation static scanner (layout thrashing, numeric jitter, WCAG 2.2, `THREE_*` hazards, `--json`, `--sarif`) |
| [scripts/preflight_gltf_budget.py](./scripts/preflight_gltf_budget.py) | Zero-mutation glTF/GLB asset auditor (triangles, draw calls, VRAM, material slots, LOD/compression coverage, URI safety) |
| [scripts/conform.py](./scripts/conform.py) | Shared family conformance validator |
| [scripts/sync-skill.sh](./scripts/sync-skill.sh) | Cross-target skill mirror sync (`check`, `sync`, `verify`, `list`) across all 8 agent homes |
| [schemas/visual-lint-report.schema.json](./schemas/visual-lint-report.schema.json) | JSON Schema `2020-12` contract for `preflight_visual_lint.py --json` |
| [schemas/gltf-budget-report.schema.json](./schemas/gltf-budget-report.schema.json) | JSON Schema `2020-12` contract for `preflight_gltf_budget.py --json` |
| [references/tactile_tokens_and_surfaces.md](./references/tactile_tokens_and_surfaces.md) | In-gamut `oklch()` color tokens, specular top-edge borders, OLED dither, WCAG 2.2 media queries, and 6-state tactile button CSS |
| [references/kinetic_physics_and_springs.md](./references/kinetic_physics_and_springs.md) | Frame-rate independent `expDecay`, `MAX_FRAME_DT`-clamped sub-stepped spring integrators, analytical harmonic oscillators, and reconciler split |
| [references/threejs_3d_asset_pipeline.md](./references/threejs_3d_asset_pipeline.md) | End-to-end 3D asset creation, Three.js materials/lighting/post-processing, procedural geometry, instancing, and render budget tiers |
| [references/preflight_scanner_notes.md](./references/preflight_scanner_notes.md) | Triage rules for scanner false positives, WCAG 2.2 signals, and `THREE_*` calibration |
| [references/phase_playbooks_and_checklists.md](./references/phase_playbooks_and_checklists.md) | Blueprint template, native GUI rules, 21-item Phase 4 checklist, CDP checks, and static print/PDF rules |
| [install_plastic_surgery.sh](./install_plastic_surgery.sh) | One-command standalone installer |

---

## Installation & Sync

### From a Git Checkout (Recommended — Syncs All 8 Agent Homes)

```bash
bash scripts/sync-skill.sh sync && bash scripts/sync-skill.sh verify
```

### Standalone Installer (Hermes / Remote)

```bash
bash install_plastic_surgery.sh
```

Or directly from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/TeacherEvan/Plastic-Surgery/main/install_plastic_surgery.sh | bash
```

---

## Usage

1. **Invoke the Skill**: Trigger `/plastic-surgery` or ask for a visual overhaul: *"Make this dashboard look modern and tactile without breaking any logic."*
2. **Run Preflight Visual Linter**:

   ```bash
   python3 ~/.hermes/skills/plastic-surgery/scripts/preflight_visual_lint.py /path/to/target --fail-on high
   ```

3. **Audit 3D Assets (when the target ships 3D)**:

   ```bash
   python3 ~/.hermes/skills/plastic-surgery/scripts/preflight_gltf_budget.py asset.glb --tier medium --fail-on high
   ```

4. **Execute the 5-Phase Pipeline**:
   - **Phase 0: Alignment Gate** -> Three axes (*Mobile/Desktop*, *Private/Commercial*, *Adult/All audiences*).
   - **Phase 1: Investigate** -> Map workspace theme, select 3–5 modern techniques, run preflight lint.
   - **Phase 2: Plan** -> Generate Plastic Surgery Blueprint.
   - **Phase 3: Implement** -> Apply presentation-layer changes in isolated CSS/presentation modules.
   - **Phase 4: Verify** -> Post-op verification (frame budgets, WCAG 2.2, zero numeric jitter, reduced-motion/contrast/forced-colors, 3D draw-call/triangle/VRAM budgets).

---

## Skill Metadata

The frontmatter in [`SKILL.md`](./SKILL.md) is the single source of truth for `name`, `description`, `version`, `author`, `platforms`, and `metadata.hermes`.

---

## Contributing & Upstream

- Canonical repository: `https://github.com/TeacherEvan/Plastic-Surgery`
- Hermes skill mirror (repertoire): `https://github.com/TeacherEvan/hermes-skills` (`skills/plastic-surgery/`)
- Never edit installed mirror copies directly; edit this git checkout and run `bash scripts/sync-skill.sh sync && bash scripts/sync-skill.sh verify`.
