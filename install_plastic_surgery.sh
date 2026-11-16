#!/usr/bin/env bash
#
# install_plastic_surgery.sh — One-command installer for the plastic-surgery skill.
#
# Deploys the runtime skill directory:
#   (SKILL.md, README.md, LICENSE, AGENTS.md,
#    scripts/preflight_visual_lint.py, scripts/preflight_gltf_budget.py,
#    references/*.md, schemas/*.json)
# into ~/.hermes/skills/plastic-surgery/ on Linux, macOS, WSL, or Termux PRoot.
#
# Usage:
#   bash install_plastic_surgery.sh
#   # or from remote:
#   curl -fsSL https://raw.githubusercontent.com/TeacherEvan/Plastic-Surgery/main/install_plastic_surgery.sh | bash
#
set -euo pipefail

SKILL_NAME="plastic-surgery"
HERMES_SKILL_DIR="$HOME/.hermes/skills/$SKILL_NAME"
RAW_BASE="https://raw.githubusercontent.com/TeacherEvan/Plastic-Surgery/main"

LOCAL_MODE=0
SOURCE="${BASH_SOURCE[0]:-}"
if [[ -n "$SOURCE" && -r "$SOURCE" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
    LOCAL_MODE=1
fi

fetch_file() {
    local dest="$1" src="$2"
    if [[ "$LOCAL_MODE" -eq 1 && "$src" != http* ]]; then
        cp "$src" "$dest"
    else
        curl -fsSL "$src" -o "$dest"
    fi
}

echo "[install_plastic_surgery] Deploying $SKILL_NAME skill..."

mkdir -p "$HERMES_SKILL_DIR/scripts"
mkdir -p "$HERMES_SKILL_DIR/references"
mkdir -p "$HERMES_SKILL_DIR/schemas"

# Remove legacy v1 filename if upgrading an older install
rm -f "$HERMES_SKILL_DIR/Plastic-Surgery.md"

# Core skill manifest & packaging metadata
for doc in SKILL.md README.md LICENSE AGENTS.md; do
    fetch_file "$HERMES_SKILL_DIR/$doc" "${SCRIPT_DIR:-$RAW_BASE}/$doc"
done

# Runtime preflight scanners
fetch_file "$HERMES_SKILL_DIR/scripts/preflight_visual_lint.py" "${SCRIPT_DIR:-$RAW_BASE}/scripts/preflight_visual_lint.py"
chmod +x "$HERMES_SKILL_DIR/scripts/preflight_visual_lint.py"

fetch_file "$HERMES_SKILL_DIR/scripts/preflight_gltf_budget.py" "${SCRIPT_DIR:-$RAW_BASE}/scripts/preflight_gltf_budget.py"
chmod +x "$HERMES_SKILL_DIR/scripts/preflight_gltf_budget.py"

# Reference documentation
for ref in \
    tactile_tokens_and_surfaces.md \
    kinetic_physics_and_springs.md \
    threejs_3d_asset_pipeline.md \
    preflight_scanner_notes.md \
    phase_playbooks_and_checklists.md; do
    fetch_file "$HERMES_SKILL_DIR/references/$ref" "${SCRIPT_DIR:-$RAW_BASE}/references/$ref"
done

# JSON Schemas (Draft 2020-12)
for schema in visual-lint-report.schema.json gltf-budget-report.schema.json; do
    fetch_file "$HERMES_SKILL_DIR/schemas/$schema" "${SCRIPT_DIR:-$RAW_BASE}/schemas/$schema"
done

chmod 755 "$HERMES_SKILL_DIR/scripts"

echo "[install_plastic_surgery] Installed to $HERMES_SKILL_DIR"
echo "[install_plastic_surgery] Files:"
find "$HERMES_SKILL_DIR" -type f -not -path '*/__pycache__/*' | sort

echo
if [[ "$LOCAL_MODE" -eq 1 && -x "$SCRIPT_DIR/scripts/sync-skill.sh" ]] && git -C "$SCRIPT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "[install_plastic_surgery] Syncing all 8 agent skill mirrors..."
  bash "$SCRIPT_DIR/scripts/sync-skill.sh" sync
else
  echo "[install_plastic_surgery] Done. The skill is now indexed by Nous Hermes Agent."
  echo "[install_plastic_surgery] Mirror sync (from repo checkout): bash scripts/sync-skill.sh sync"
fi
echo "[install_plastic_surgery] OpenCode:    ~/.config/opencode/skills/plastic-surgery/"
echo "[install_plastic_surgery] Antigravity: ~/.gemini/antigravity-cli/skills/plastic-surgery/ or ~/.agents/skills/plastic-surgery/"
echo "[install_plastic_surgery] Gemini CLI:  ~/.gemini/skills/plastic-surgery/ and ~/.gemini/surgical/plastic-surgery/"
echo "[install_plastic_surgery] Cursor:      ~/.cursor/skills/plastic-surgery/"
echo "[install_plastic_surgery] VS Code:     ~/.copilot/skills/plastic-surgery/"
