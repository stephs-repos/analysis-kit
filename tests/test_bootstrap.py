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


def test_reference_raw_data_directory_exists(scaffolded_project: Path) -> None:
    """Regression: every doc tells users to drop data into reference/raw-data/.
    The directory must exist after scaffolding so the instruction isn't a lie.
    """
    p = scaffolded_project / "reference" / "raw-data"
    assert p.exists() and p.is_dir(), "reference/raw-data/ must be created by bootstrap"
    # README inside it documents the convention and keeps the directory tracked
    # despite the gitignore on raw-data/* contents.
    assert (p / "README.md").exists()


def test_skills_have_valid_frontmatter() -> None:
    """Every skill must have YAML frontmatter with name + description."""
    import re
    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    assert skills_dir.exists(), "skills/ directory must exist"
    found = list(skills_dir.glob("*.md"))
    assert len(found) >= 4, f"expected ≥4 skills, found {len(found)}"
    for skill in found:
        txt = skill.read_text()
        assert txt.startswith("---\n"), f"{skill.name} missing YAML frontmatter"
        m = re.match(r"^---\n(.*?)\n---\n", txt, re.DOTALL)
        assert m, f"{skill.name} frontmatter not closed"
        fm = m.group(1)
        assert "name:" in fm, f"{skill.name} frontmatter missing name:"
        assert "description:" in fm, f"{skill.name} frontmatter missing description:"


def test_install_skills_substitutes_kit_root(tmp_path: Path) -> None:
    """install-skills.sh must replace __AKIT_ROOT__ with the kit's absolute path."""
    import os
    import subprocess
    kit_root = Path(__file__).resolve().parent.parent
    script = kit_root / "bootstrap" / "install-skills.sh"
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run([str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    skills = tmp_path / ".claude" / "skills"
    assert skills.exists()
    # Substitution: at least one skill (akit-start) references AKIT_ROOT
    start_md = (skills / "akit-start.md").read_text()
    assert "__AKIT_ROOT__" not in start_md, "token should have been substituted"
    assert str(kit_root) in start_md, "kit absolute path should be in installed skill"


def test_reference_directory_has_convention_readme(scaffolded_project: Path) -> None:
    """Regression: reference/README.md documents the raw-data-vs-reference
    split (briefs/dictionaries go in reference/, data files go in raw-data/).
    Must exist so the convention is discoverable from the directory listing.
    """
    p = scaffolded_project / "reference" / "README.md"
    assert p.exists(), "reference/README.md must be created by bootstrap"
    txt = p.read_text()
    # sanity-check it documents the split
    assert "raw-data" in txt
    assert "brief" in txt.lower() or "dictionary" in txt.lower()


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


def test_check_must_customize_clean_after_markers_filled(scaffolded_project: Path) -> None:
    """Regression: once the real ``{{MUST_CUSTOMIZE …}}`` placeholders are filled,
    the checker must report success — even though onboarding docs (README,
    CLAUDE.md) legitimately mention the bare word ``MUST_CUSTOMIZE`` in prose.

    The checker keys on the literal placeholder opening, not the bare word, so
    documentation about markers must not keep a project perpetually 'unfilled'.
    """
    import re

    marker = re.compile(r"\{\{MUST_CUSTOMIZE[^}]*\}\}")
    for f in scaffolded_project.rglob("*"):
        if not f.is_file():
            continue
        try:
            txt = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        filled = marker.sub("filled in", txt)
        if filled != txt:
            f.write_text(filled)

    script = Path(__file__).resolve().parent.parent / "bootstrap" / "check-must-customize.sh"
    result = subprocess.run([str(script), str(scaffolded_project)], capture_output=True, text=True)
    assert result.returncode == 0, (
        "checker should report clean once real markers are filled; "
        f"stdout:\n{result.stdout}"
    )
    assert "no MUST_CUSTOMIZE markers remain" in result.stdout


def test_manifest_pins_framework_version(scaffolded_project: Path) -> None:
    manifest = json.loads((scaffolded_project / "analysis-kit.json").read_text())
    assert manifest["framework_version"] == "1.0.0"
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


def _scaffold(base: Path, tier: str) -> Path:
    target = base / "proj"
    bootstrap = Path(__file__).resolve().parent.parent / "bootstrap" / "new-project.sh"
    subprocess.run(
        [str(bootstrap), str(target), tier, "--name", "test-proj", "--github-user", "tester"],
        check=True,
        capture_output=True,
    )
    return target


def test_full_tier_has_render_pipeline(tmp_path: Path) -> None:
    """Full tier ships a renderable vignette stack AND the deps to render it.

    Regression: the vignette template imports matplotlib and uses Quarto's
    Jupyter engine (needs jupyter + pyyaml), which were historically absent from
    requirements.txt — so a fresh full-tier project could not render a vignette.
    """
    p = _scaffold(tmp_path, "--full")
    assert (p / "vignettes").exists()
    assert (p / "_quarto.yml").exists()
    reqs = (p / "requirements.txt").read_text()
    for dep in ("matplotlib", "jupyter", "pyyaml"):
        assert dep in reqs, f"full-tier requirements.txt missing {dep}"


def test_rebuild_pipeline_files_present_both_tiers(tmp_path: Path) -> None:
    """The Makefile and CI trust-gate ship in every tier: validate/findings apply
    regardless, and the render target self-skips when there's no _quarto.yml."""
    for tier in ("--minimum", "--full"):
        p = _scaffold(tmp_path / tier.strip("-"), tier)
        assert (p / "Makefile").exists(), f"{tier}: Makefile missing"
        assert (p / ".github" / "workflows" / "trust-contract.yml").exists(), f"{tier}: CI missing"


def test_minimum_tier_strips_render_deps(tmp_path: Path) -> None:
    """Minimum projects have no vignettes, so the render-only deps are stripped,
    but the base deps and the pinning note remain."""
    p = _scaffold(tmp_path, "--minimum")
    reqs = (p / "requirements.txt").read_text()
    assert "matplotlib" not in reqs
    assert "jupyter" not in reqs
    assert "pandas" in reqs
    assert "Pinning note" in reqs
