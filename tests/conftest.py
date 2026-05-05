"""Shared pytest fixtures."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = KIT_ROOT / "templates"
BOOTSTRAP = KIT_ROOT / "bootstrap" / "new-project.sh"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic"


@pytest.fixture
def scaffolded_project(tmp_path: Path) -> Path:
    """Bootstrap a fresh --minimum project into tmp_path/proj and return its root."""
    target = tmp_path / "proj"
    subprocess.run(
        [str(BOOTSTRAP), str(target), "--minimum", "--name", "test-proj", "--github-user", "tester"],
        check=True,
        capture_output=True,
    )
    return target


@pytest.fixture
def project_with_fixture(scaffolded_project: Path) -> Path:
    """A scaffolded project with the synthetic dataset copied into reference/raw-data/."""
    raw = scaffolded_project / "reference" / "raw-data"
    raw.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE_DIR / "sessions.csv", raw / "sessions.csv")
    return scaffolded_project
