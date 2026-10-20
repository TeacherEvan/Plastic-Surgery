#!/usr/bin/env bash
#
# install_plastic_surgery.sh — One-command installer for the plastic-surgery skill.
#
# Deploys the complete skill directory:
#   (SKILL.md, scripts/preflight_visual_lint.py,
#    references/tactile_tokens_and_surfaces.md, references/kinetic_physics_and_springs.md)
# into ~/.hermes/skills/plastic-surgery/ on Linux, macOS, WSL, or Termux PRoot.
#
# Usage:
#   bash install_plastic_surgery.sh
#   # or from remote:
#   curl -fsSL https://raw.githubusercontent.com/TeacherEvan/Plastic-Surgery/main/install_plastic_surgery.sh | bash
#
set -eo pipefail

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

# Core skill manifest
fetch_file "$HERMES_SKILL_DIR/SKILL.md" "${SCRIPT_DIR:-$RAW_BASE}/SKILL.md"

# Preflight visual & compositor scanner
fetch_file "$HERMES_SKILL_DIR/scripts/preflight_visual_lint.py" "${SCRIPT_DIR:-$RAW_BASE}/scripts/preflight_visual_lint.py"
chmod +x "$HERMES_SKILL_DIR/scripts/preflight_visual_lint.py"

# Reference documentation
fetch_file "$HERMES_SKILL_DIR/references/tactile_tokens_and_surfaces.md" "${SCRIPT_DIR:-$RAW_BASE}/references/tactile_tokens_and_surfaces.md"
fetch_file "$HERMES_SKILL_DIR/references/kinetic_physics_and_springs.md" "${SCRIPT_DIR:-$RAW_BASE}/references/kinetic_physics_and_springs.md"

chmod 755 "$HERMES_SKILL_DIR/scripts"

echo "[install_plastic_surgery] Installed to $HERMES_SKILL_DIR"
echo "[install_plastic_surgery] Files:"
find "$HERMES_SKILL_DIR" -type f -not -path '*/__pycache__/*' | sort

echo
echo "[install_plastic_surgery] Done. The skill is now indexed by Nous Hermes Agent."
echo "[install_plastic_surgery] OpenCode:    copy into ~/.config/opencode/skills/plastic-surgery/"
echo "[install_plastic_surgery] Antigravity: copy into ~/.config/antigravity/skills/plastic-surgery/ or .agents/skills/plastic-surgery/"
echo "[install_plastic_surgery] Cursor:      copy into ~/.cursor/skills/plastic-surgery/"
