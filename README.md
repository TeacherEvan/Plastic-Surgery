# Plastic-Surgery

**UI / GUI / Dashboard Visual Overhaul** — the visual counterpart to `surgical-implementation`.

Plastic Surgery is a Hermes Agent skill (and mirrored to Google Antigravity and Opencode) that performs precision cosmetic and rendering overhauls on UI, GUI, and dashboards: tactile buttons, perceptual colour tokens, animation smoothing, compositor-clean rendering, and workspace-themed design — while guaranteeing **100% functional regression safety**.

## Skill directory

| Target | Location |
|---|---|
| Nous Hermes Agent (user skills) | `~/.hermes/skills/plastic-surgery/` |
| Google Antigravity | `~/.config/antigravity/skills/plastic-surgery/` |
| Opencode | `~/.config/opencode/skills/plastic-surgery/` |
| Canonical repo (github) | `github.com/TeacherEvan/Plastic-Surgery` |
| Hermes skill mirror (repatoir) | `github.com/TeacherEvan/hermes-skills` (`skills/plastic-surgery/`) |

## What it covers

- **Alignment Gate** → three axes (Mobile/Desktop, Private/Commercial, Adult/All audiences); halt-and-ask if unverifiable
- **Collaboration State** → the three orientation questions (1–2 follow-ups max)
- **Investigate** → workspace theme mapping + 3–5 modern technique selection
- **Plan** → Plastic Surgery Blueprint (tokens, six-state tactile buttons, rendering plan)
- **Implement** → presentation-layer-only changes; functional bindings preserved
- **Verify** → post-op checklist (frame budgets, INP/CLS, overdraw, no-numeric-jitter, reduced-motion)

Full specification: `SKILL.md`.

## Skill metadata (standard frontmatter)

```yaml
name: plastic-surgery
description: "Use when performing a precision UI/GUI/Dashboard visual overhaul (\"Plastic Surgery\")."
version: 1.0.0
author: Fenrie (Lea's AI wolf), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
category: creative
tags: [ui, gui, dashboard, design, visual, accessibility, animations, rendering, plastic-surgery, workspace-theme]
metadata:
  hermes:
    category: creative
    tags: [visual, ui-overhaul, design-system, assessment, creative]
```

## Contributing

- Fork the canonical repo and open a PR against `main`.
- Never edit a peer skill's files without explicit OK (see `Junto` rule).
- Mirror the layout of an existing sibling skill (e.g. `surgical-audit`).
