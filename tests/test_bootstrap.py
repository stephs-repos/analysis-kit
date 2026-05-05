"""Test that bootstrap/new-project.sh produces a working project."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_minimum_tier_has_required_files(scaffolded_project: Path) -> None:
    p = scaffolded_project
    assert (p / "CLAUDE.md").exists()
    assert (p / "README.md").exists()
    assert (p / "analysis-kit.json").exists()
    assert (p / "analysis" / "validate.py").exists()
    assert (p / "analysis" / "_findings.py").exists()
    assert (p / "analysis" / "_decisions.py").exists()
    assert (p / "analysis" / "schemas.py").exists()
    assert (p / "analysis" / "output" / "findings.json").exists()
    assert (p / "live-docs" / "TRUST_MEMO.md").exists()
    assert (p / "live-docs" / "DECISIONS.md").exists()
    assert (p / "live-docs" / "METHODOLOGY_LOG.md").exists()
    assert (p / "memory" / "MEMORY.md").exists()
    assert (p / "memory" / "data_quality_caveats.md").exists()
    assert (p / ".claude" / "settings.json").exists()
    assert (p / ".claude" / "hooks" / "validate-on-stop.sh").exists()
    assert (p / ".claude" / "hooks" / "block-unvalidated-commit.sh").exists()


def test_minimum_tier_omits_full_extras(scaffolded_project: Path) -> None:
    p = scaffolded_project
    assert not (p / "vignettes").exists()
    assert not (p / "_quarto.yml").exists()


def test_hooks_are_executable(scaffolded_project: Path) -> None:
    import os
    for hook in (scaffolded_project / ".claude" / "hooks").glob("*.sh"):
        assert os.access(hook, os.X_OK), f"{hook.name} is not executable"


def test_token_substitution(scaffolded_project: Path) -> None:
    claude_md = (scaffolded_project / "CLAUDE.md").read_text()
    assert "{{PROJECT_NAME}}" not in claude_md
    assert "test-proj" in claude_md
    assert "{{FRAMEWORK_VERSION}}" not in claude_md


def test_must_customize_markers_remain(scaffolded_project: Path) -> None:
    """MUST_CUSTOMIZE should remain — it's intentional, marks places the project must fill."""
    txt = (scaffolded_project / "CLAUDE.md").read_text()
    assert "MUST_CUSTOMIZE" in txt or "{{MUST_CUSTOMIZE" in txt


def test_check_must_customize_detects_unfilled(scaffolded_project: Path) -> None:
    script = Path(__file__).resolve().parent.parent / "bootstrap" / "check-must-customize.sh"
    result = subprocess.run([str(script), str(scaffolded_project)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "MUST_CUSTOMIZE" in result.stdout


def test_manifest_pins_framework_version(scaffolded_project: Path) -> None:
    manifest = json.loads((scaffolded_project / "analysis-kit.json").read_text())
    assert manifest["framework_version"] == "0.1.0"
    assert manifest["tier"] == "minimum"
    assert manifest["project_name"] == "test-proj"


def test_git_initialised_with_first_commit(scaffolded_project: Path) -> None:
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=scaffolded_project,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "scaffold from analysis-kit" in result.stdout


def test_refuses_to_overwrite_nonempty_target(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "stuff.txt").write_text("don't clobber me")
    bootstrap = Path(__file__).resolve().parent.parent / "bootstrap" / "new-project.sh"
    result = subprocess.run([str(bootstrap), str(target)], capture_output=True, text=True)
    assert result.returncode != 0
