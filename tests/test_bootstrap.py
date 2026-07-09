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
    # Claude Code only discovers <name>/SKILL.md directories — flat .md files
    # in skills/ are silently ignored ("unknown command").
    start_md = (skills / "akit-start" / "SKILL.md").read_text()
    assert "__AKIT_ROOT__" not in start_md, "token should have been substituted"
    assert str(kit_root) in start_md, "kit absolute path should be in installed skill"
    assert not list(skills.glob("*.md")), "no flat .md files — they are not discovered"


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


def test_marker_taxonomy(scaffolded_project: Path) -> None:
    """Two token classes with a hard boundary. MUST_CUSTOMIZE = the six setup
    markers /akit-fill walks (project_overview is the single source; the
    CLAUDE.md goal and README description are distillations of it). FIRST_ENTRY
    = lifecycle stubs that resolve during analysis — they must NOT carry the
    setup token or the grep-clean invariant ('set up when the scan returns
    nothing') becomes unreachable before the first DR-NNN exists."""
    import re
    p = scaffolded_project
    setup_re = re.compile(r"\{\{MUST_CUSTOMIZE", re.DOTALL)

    def markers(rel: str) -> int:
        return len(setup_re.findall((p / rel).read_text()))

    setup_files = {
        "CLAUDE.md": 1,
        "README.md": 1,
        "memory/project_overview.md": 1,
        "memory/stakeholder_stance.md": 1,
        "memory/data_quality_caveats.md": 1,
        "live-docs/DATA_PROFILE.md": 1,
    }
    for rel, n in setup_files.items():
        assert markers(rel) == n, f"{rel}: expected {n} setup marker(s), got {markers(rel)}"

    # Total setup markers across the scaffold is exactly the six above.
    total = sum(
        len(setup_re.findall(f.read_text()))
        for f in p.rglob("*")
        if f.is_file() and f.suffix in {".md", ".py", ".json"} and ".claude" not in f.parts
    )
    assert total == 6, f"expected exactly 6 setup markers, found {total}"

    # Lifecycle stubs carry FIRST_ENTRY, never the setup token.
    for rel in (
        "live-docs/DECISIONS.md", "live-docs/ANALYSIS_BACKLOG.md",
        "live-docs/METHODOLOGY_LOG.md", "live-docs/TOOLING.md",
        "live-docs/TRUST_MEMO.md", "analysis/_decisions.py",
        "analysis/schemas.py", "analysis/01_inspect_raw.py", "analysis/02_profile.py",
    ):
        txt = (p / rel).read_text()
        assert "{{FIRST_ENTRY" in txt, f"{rel}: lifecycle stub missing FIRST_ENTRY"
        assert not setup_re.search(txt), f"{rel}: lifecycle stub must not carry the setup token"

    # Single-source wiring: the two distillation markers name their source.
    for rel in ("CLAUDE.md", "README.md"):
        assert "project_overview.md" in (p / rel).read_text(), \
            f"{rel}: distillation marker must name memory/project_overview.md as its source"

    # And the scanner must ignore FIRST_ENTRY: fill only the setup markers,
    # then expect a clean report despite all nine lifecycle stubs remaining.
    full_marker = re.compile(r"\{\{MUST_CUSTOMIZE.*?\}\}", re.DOTALL)
    for f in p.rglob("*"):
        if not f.is_file() or ".claude" in f.parts:
            continue
        try:
            txt = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        filled = full_marker.sub("filled in", txt)
        if filled != txt:
            f.write_text(filled)
    scanner = p / ".claude" / "akit" / "check-must-customize.sh"
    result = subprocess.run(["bash", str(scanner), str(p)], capture_output=True, text=True)
    assert result.returncode == 0, f"scanner must ignore FIRST_ENTRY stubs:\n{result.stdout}"


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


def test_manifest_records_kit_provenance(scaffolded_project: Path) -> None:
    """framework_version outlives template changes, so 'which templates made this
    scaffold?' must be answerable from the project itself: the manifest and the
    scaffold commit both record the kit commit that produced it."""
    kit_root = Path(__file__).resolve().parent.parent
    head = subprocess.run(
        ["git", "-C", str(kit_root), "rev-parse", "--short=12", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()
    manifest = json.loads((scaffolded_project / "analysis-kit.json").read_text())
    assert "{{" not in manifest["kit_commit"], "token not substituted"
    if head:  # git metadata available (not a tarball install)
        assert manifest["kit_commit"] in (head, f"{head}-dirty")
    assert manifest["kit_url"].startswith("http"), manifest["kit_url"]
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=scaffolded_project,
        capture_output=True, text=True, check=True,
    ).stdout
    assert manifest["kit_commit"] in log, "scaffold commit message must carry the kit commit"


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


def test_quickstart_ships_in_every_project(tmp_path: Path) -> None:
    """QUICKSTART.md is the new-user recipe; it must land in both tiers, and the
    README must point at it so it's discoverable from a fresh clone."""
    for tier in ("--minimum", "--full"):
        p = _scaffold(tmp_path / tier.strip("-"), tier)
        qs = p / "QUICKSTART.md"
        assert qs.exists(), f"{tier}: QUICKSTART.md missing"
        body = qs.read_text()
        assert "/akit-fill" in body and "/akit-finding" in body, "quickstart should name the core skills"
        assert "/akit-next" in body, "quickstart's primary interface is the conductor"
        assert "QUICKSTART.md" in (p / "README.md").read_text(), f"{tier}: README must link QUICKSTART"


def test_cheat_sheet_ships_in_every_project(tmp_path: Path) -> None:
    """CHEAT_SHEET.md is the task→command lookup that complements QUICKSTART.md;
    it must land in both tiers and be reachable from both entry docs."""
    for tier in ("--minimum", "--full"):
        p = _scaffold(tmp_path / tier.strip("-"), tier)
        cs = p / "CHEAT_SHEET.md"
        assert cs.exists(), f"{tier}: CHEAT_SHEET.md missing"
        body = cs.read_text()
        for must in ("/akit-finding", "validate.py", "DR-NNN", "/akit-next"):
            assert must in body, f"{tier}: cheat sheet missing {must}"
        assert "CHEAT_SHEET.md" in (p / "README.md").read_text(), f"{tier}: README must link the cheat sheet"
        assert "CHEAT_SHEET.md" in (p / "QUICKSTART.md").read_text(), f"{tier}: QUICKSTART must link the cheat sheet"


def test_kit_repo_url_substituted(tmp_path: Path) -> None:
    """The 'scaffolded from' links must carry the kit clone's real origin URL,
    not a guess built from --github-user — that guess produced dead links
    whenever the kit lived under a different account than the project author."""
    kit_root = Path(__file__).resolve().parent.parent
    origin = subprocess.run(
        ["git", "-C", str(kit_root), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    ).stdout.strip()
    p = _scaffold(tmp_path, "--minimum")
    for doc in ("README.md", "CLAUDE.md"):
        txt = (p / doc).read_text()
        assert "{{KIT_REPO_URL}}" not in txt, f"{doc}: token not substituted"
        if origin:
            expected = origin.removesuffix(".git")
            if expected.startswith("git@"):
                expected = "https://" + expected.removeprefix("git@").replace(":", "/", 1)
            elif expected.startswith("ssh://git@"):
                expected = "https://" + expected.removeprefix("ssh://git@")
            assert expected in txt, f"{doc}: expected kit link {expected}"
        else:
            # No remote (tarball install) — falls back to the github-user guess.
            assert "https://github.com/tester/analysis-kit" in txt, doc


def test_akit_next_skill_installed(tmp_path: Path) -> None:
    """install-skills.sh must install the /akit-next conductor with its kit-root
    token substituted (it shells out to bootstrap/check-must-customize.sh)."""
    import os
    kit_root = Path(__file__).resolve().parent.parent
    script = kit_root / "bootstrap" / "install-skills.sh"
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run([str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    installed = tmp_path / ".claude" / "skills" / "akit-next" / "SKILL.md"
    assert installed.exists(), "akit-next SKILL.md not installed (missing from SKILL_NAMES?)"
    txt = installed.read_text()
    assert "__AKIT_ROOT__" not in txt, "kit-root token should have been substituted"
    assert str(kit_root) in txt


def test_scaffold_embeds_project_skills(tmp_path: Path) -> None:
    """Scaffolds embed the in-project skills (.claude/skills/<name>/SKILL.md —
    auto-discovered by Claude Code) plus the marker-scanner, so /akit-next works
    for anyone who clones the project with no per-machine install."""
    import os
    import stat
    p = _scaffold(tmp_path, "--minimum")
    for skill in ("akit", "akit-fill", "akit-finding", "akit-next"):
        sk = p / ".claude" / "skills" / skill / "SKILL.md"
        assert sk.exists(), f"embedded skill missing: {skill}"
        assert "__AKIT_ROOT__" not in sk.read_text(), f"{skill}: kit-root token unsubstituted"
    assert not (p / ".claude" / "skills" / "akit-start").exists(), \
        "akit-start needs the kit clone — must not be embedded"
    scanner = p / ".claude" / "akit" / "check-must-customize.sh"
    assert scanner.exists() and os.stat(scanner).st_mode & stat.S_IXUSR, "scanner missing or not executable"
    # Self-match regression: the embedded scanner and skills must never be
    # reported as unfilled markers (the scanner's own MARKER= line, and skill
    # prose about markers, used to trip this).
    result = subprocess.run(["bash", str(scanner), str(p)], capture_output=True, text=True)
    assert ".claude/" not in result.stdout, f"scanner flagged kit-managed files:\n{result.stdout}"


def test_akit_index_references_next(tmp_path: Path) -> None:
    """The /akit index must point at the conductor so it's discoverable."""
    index = (Path(__file__).resolve().parent.parent / "skills" / "akit.md").read_text()
    assert "/akit-next" in index, "akit.md index does not mention /akit-next"
