"""Conformance, schema, documentation, and sync tests for plastic-surgery."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import jsonschema
import yaml

REPO = Path(__file__).resolve().parent.parent
CONFORM = REPO / "scripts" / "conform.py"
SYNC_SCRIPT = REPO / "scripts" / "sync-skill.sh"
SKILL_MD = REPO / "SKILL.md"
SCHEMAS_DIR = REPO / "schemas"
SKILL_NAME = "plastic-surgery"

ASSET_REF = re.compile(
    r"(?<![A-Za-z0-9_./~-])(?:\./)?(references|scripts|schemas)/([A-Za-z0-9._-]+)"
)


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    assert text.startswith("---"), "SKILL.md must start with ---"
    close = re.search(r"\n---\s*(?:\n|$)", text[3:])
    assert close is not None, "SKILL.md frontmatter must close with ---"
    raw_fm = text[3 : close.start() + 3]
    body = text[close.end() + 3 :]
    loaded = yaml.safe_load(raw_fm)
    assert isinstance(loaded, dict), "Frontmatter must be a mapping"
    return loaded, body


class SkillConformanceTests(unittest.TestCase):
    def test_conform_gate_passes(self) -> None:
        r = subprocess.run(
            [sys.executable, "-B", str(CONFORM)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
        self.assertIn("PASS  PlasticSurgery", r.stdout)

    def test_skill_md_frontmatter_and_line_budget(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertLessEqual(len(lines), 250, f"SKILL.md is {len(lines)} lines (>250)")

        fm, body = _split_frontmatter(text)
        self.assertEqual(fm["name"], SKILL_NAME)
        self.assertEqual(fm["version"], "1.4.0")
        desc = fm["description"]
        self.assertIsInstance(desc, str)
        self.assertLessEqual(len(desc), 60)
        self.assertTrue(desc.startswith("Use when"))
        self.assertTrue(desc.endswith("."))

        for folder, rel in ASSET_REF.findall(body):
            self.assertTrue(
                (REPO / folder / rel).exists(),
                f"SKILL.md body references missing {folder}/{rel}",
            )

    def test_repo_packaging_hygiene(self) -> None:
        self.assertFalse(
            (REPO / "Plastic-Surgery.md").exists(),
            "Legacy Plastic-Surgery.md must be removed",
        )
        self.assertTrue((REPO / "LICENSE").exists())
        self.assertTrue((REPO / "AGENTS.md").exists())
        nested = [
            p for p in REPO.rglob("SKILL.md") if p != SKILL_MD and ".git" not in p.parts
        ]
        self.assertEqual(nested, [])

    def test_schemas_are_valid_draft_2020_12(self) -> None:
        for schema_file in sorted(SCHEMAS_DIR.glob("*.json")):
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
            self.assertEqual(
                schema.get("$schema"),
                "https://json-schema.org/draft/2020-12/schema",
            )
            self.assertFalse(schema.get("unevaluatedProperties", True))
            jsonschema.Draft202012Validator.check_schema(schema)


class SyncSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ps-sync-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        self.home.mkdir()

    def _run_sync(self, mode: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        env.pop("SKILL_TARGETS", None)
        return subprocess.run(
            ["bash", str(SYNC_SCRIPT), mode],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(REPO),
            check=False,
        )

    def test_sync_and_verify_with_hermetic_home(self) -> None:
        # Simulate an existing stale install carrying legacy Plastic-Surgery.md and conform.py
        hermes_dest = self.home / ".hermes" / "skills" / SKILL_NAME
        (hermes_dest / "scripts").mkdir(parents=True)
        (hermes_dest / "Plastic-Surgery.md").write_text("legacy", encoding="utf-8")
        (hermes_dest / "scripts" / "conform.py").write_text("stale", encoding="utf-8")

        # Symlink ~/.config/opencode/skills to ~/.hermes/skills to test deduplication
        opencode_parent = self.home / ".config" / "opencode"
        opencode_parent.mkdir(parents=True)
        (opencode_parent / "skills").symlink_to(self.home / ".hermes" / "skills")

        r_check = self._run_sync("check")
        self.assertEqual(r_check.returncode, 1)

        r_sync = self._run_sync("sync")
        self.assertEqual(r_sync.returncode, 0, f"{r_sync.stdout}\n{r_sync.stderr}")
        self.assertIn("[DEDUPE]", r_sync.stderr)

        # Runtime scripts ARE mirrored; repo-only scripts and legacy doc are NOT present
        self.assertTrue(
            (hermes_dest / "scripts" / "preflight_visual_lint.py").is_file()
        )
        self.assertTrue(
            (hermes_dest / "scripts" / "preflight_gltf_budget.py").is_file()
        )
        self.assertFalse((hermes_dest / "scripts" / "conform.py").exists())
        self.assertFalse((hermes_dest / "scripts" / "sync-skill.sh").exists())
        self.assertFalse((hermes_dest / "Plastic-Surgery.md").exists())
        self.assertFalse((hermes_dest / "tests").exists())
        self.assertFalse((hermes_dest / ".github").exists())

        r_verify = self._run_sync("verify")
        self.assertEqual(
            r_verify.returncode, 0, f"{r_verify.stdout}\n{r_verify.stderr}"
        )
        self.assertIn("Verified: 7 install(s) match the repo.", r_verify.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
