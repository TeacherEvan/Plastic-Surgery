# Plastic-Surgery

**UI / GUI / Dashboard Visual Overhaul** — the visual counterpart to `surgical-implementation`.

Plastic Surgery is a high-craft agent skill for **Nous Hermes Agent**, **Google Antigravity**, **OpenCode**, and **Cursor** that performs precision cosmetic and rendering overhauls on UI, GUI, and dashboards: tactile buttons, perceptual `oklch()` colour tokens, sub-stepped spring physics, compositor-clean animations, and workspace-themed design — while guaranteeing **100% functional regression safety**.

---

## Files & Repository Architecture

| File | Purpose |
|---|---|
| `SKILL.md` | Core skill manifest + 5-phase overhaul pipeline (Alignment -> Investigate -> Plan -> Implement -> Verify) |
| `scripts/preflight_visual_lint.py` | Zero-mutation static AST & CSS scanner (detects layout thrashing, numeric jitter, blur overdraw, reduced-motion gaps) |
| `references/tactile_tokens_and_surfaces.md` | Perceptual `oklch()` color tokens, specular top-edge borders, OLED anti-banding dither, and 6-state tactile button specification |
| `references/kinetic_physics_and_springs.md` | Frame-rate independent `expDecay`, dynamic sub-stepped symplectic spring integrators, analytical harmonic oscillators, and frame budget tables |
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
3. **Execute the 5-Phase Pipeline**:
   - **Phase 0: Alignment Gate** $\rightarrow$ Three axes (*Mobile/Desktop*, *Private/Commercial*, *Adult/All audiences*). Halts and asks if unaligned.
   - **Phase 1: Investigate** $\rightarrow$ Map workspace theme, select 3–5 modern techniques, run preflight lint.
   - **Phase 2: Plan** $\rightarrow$ Generate Plastic Surgery Blueprint.
   - **Phase 3: Implement** $\rightarrow$ Apply presentation-layer changes in isolated CSS/presentation modules.
   - **Phase 4: Verify** $\rightarrow$ Post-op verification (frame budgets, INP/CLS, zero numeric jitter, reduced-motion guard).

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
