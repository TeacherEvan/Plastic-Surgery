# AGENTS.md — PlasticSurgery

Repository conventions and verification commands for agents modifying the `plastic-surgery` skill.

## Purpose & Contract

`PlasticSurgery` is a visual-only UI/GUI/dashboard/3D Three.js/video overhaul skill paired with four stdlib-only tools:
[`scripts/preflight_visual_lint.py`](./scripts/preflight_visual_lint.py) (2D CSS/JS/TS/MJS/HTML + WCAG 2.2 + Three.js hazards, JSON & SARIF `2.1.0`),
[`scripts/preflight_gltf_budget.py`](./scripts/preflight_gltf_budget.py) (glTF/GLB triangle, draw-call, VRAM, compression, LOD, and scale budgets),
[`scripts/preflight_video_polish.py`](./scripts/preflight_video_polish.py) (`surgical-media` storyboard & MP4 finishing auditor), and
[`scripts/polish_surgical_media.py`](./scripts/polish_surgical_media.py) (non-destructive Mode A storyboard & Mode B FFmpeg polish engine).
All changes preserve the core surgical mandate: **functional logic, bindings, contracts, and 3D scene graphs are immutable**.

## Build, Test & Lint Commands

Run checks from the `PlasticSurgery/` repository root with isolated cache paths so no untracked cache artifacts pollute the tree:

```bash
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"
python3 -B scripts/conform.py
pytest -o cache_dir=/tmp/ps-pytest -q tests/
ruff check --no-cache scripts/ tests/
ruff format --check --no-cache scripts/ tests/
mypy --cache-dir /tmp/ps-mypy --strict --ignore-missing-imports scripts/ tests/
shellcheck -x install_plastic_surgery.sh scripts/sync-skill.sh
yamllint .github/workflows/skill-ci.yml
check-jsonschema --check-metaschema schemas/*.json
```

## Mirrored vs Repo-Only Boundaries

| Path | Mirrored to Agent Homes | Notes |
| :--- | :--- | :--- |
| `SKILL.md`, `README.md`, `LICENSE`, `AGENTS.md` | Yes | Canonical manifest & docs |
| `references/`, `schemas/` | Yes | Progressive-disclosure docs & JSON Schema `2020-12` contracts |
| `scripts/preflight_visual_lint.py`, `scripts/preflight_gltf_budget.py`, `scripts/preflight_video_polish.py`, `scripts/polish_surgical_media.py` | Yes | Runtime skill scanners & polishers executed during Phase 1–4 |
| `scripts/conform.py`, `scripts/sync-skill.sh` | No (Repo-only) | Governance & distribution helpers |
| `tests/`, `.github/`, `__pycache__/`, `.*_cache/` | No (Repo-only) | CI, tests, and local caches |

## Source-of-Truth Invariant

Never edit installed skill copies inside `~/.hermes/skills/plastic-surgery/`, `~/.config/opencode/skills/plastic-surgery/`, `~/.gemini/*/plastic-surgery/`, `~/.cursor/skills/plastic-surgery/`, `~/.copilot/skills/plastic-surgery/`, or `~/.agents/skills/plastic-surgery/`. Edit this git repository and sync every target with:

```bash
bash scripts/sync-skill.sh sync && bash scripts/sync-skill.sh verify
```

## Security, Authoring & Naming Rules

- Maintain `SKILL.md` frontmatter `description` `<= 60` chars (`"Use when ... ."`) and body `<= 250` lines.
- Use bare lowercase-hyphenated identifiers in `related_skills` (`^[a-z0-9-]+$`).
- Enforce path containment (`Path.resolve()` + `is_relative_to()`) when reading external glTF/buffer/image URIs; never traverse outside the asset's base directory.
- Keep `scripts/preflight_*.py` strictly stdlib-only and read-only on target codebases.
- Never include personal data, secrets, or local user paths in tracked files or tests.
