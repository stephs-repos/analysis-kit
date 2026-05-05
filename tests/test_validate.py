"""Test the validate.py contract end-to-end against the synthetic fixture."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def write_findings(project: Path, findings: list[dict]) -> None:
    out = project / "analysis" / "output" / "findings.json"
    out.write_text(json.dumps(findings, indent=2))


def run_validate(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python", "analysis/validate.py", *args],
        cwd=project,
        capture_output=True,
        text=True,
    )


# ── empty findings = green ──────────────────────────────────────────────────

def test_empty_findings_passes(scaffolded_project: Path) -> None:
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode == 0, result.stdout + result.stderr


# ── structural failures ─────────────────────────────────────────────────────

def test_missing_required_field_fails(scaffolded_project: Path) -> None:
    write_findings(scaffolded_project, [{"id": "F-001"}])  # missing everything else
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "missing required field" in result.stdout


def test_invalid_check_type_fails(scaffolded_project: Path) -> None:
    f = _minimal_finding()
    f["check_type"] = "bogus_type"
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "unknown check_type" in result.stdout


def test_observed_without_measurement_ref_fails(scaffolded_project: Path) -> None:
    f = _minimal_finding()
    f["counterfactual_tag"] = "OBSERVED"
    f.pop("measurement_ref", None)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "OBSERVED requires measurement_ref" in result.stdout


def test_duplicate_id_fails(scaffolded_project: Path) -> None:
    f1 = _minimal_finding(fid="F-001")
    f2 = _minimal_finding(fid="F-001")
    write_findings(scaffolded_project, [f1, f2])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "duplicate" in result.stdout


def test_orphan_id_in_trust_memo_fails(scaffolded_project: Path) -> None:
    write_findings(scaffolded_project, [_minimal_finding()])
    tm = scaffolded_project / "live-docs" / "TRUST_MEMO.md"
    tm.write_text(tm.read_text() + "\n\nSee `F-999` for details.\n")
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "F-999" in result.stdout


def test_unresolved_code_path_fails(scaffolded_project: Path) -> None:
    f = _minimal_finding()
    f["code_path"] = "analysis/does_not_exist.py:fn"
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "not found" in result.stdout


def test_revision_history_required(scaffolded_project: Path) -> None:
    f = _minimal_finding()
    f["revision_history"] = []
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "revision_history" in result.stdout


# ── structural passes ───────────────────────────────────────────────────────

def test_well_formed_finding_passes_fast(scaffolded_project: Path) -> None:
    write_findings(scaffolded_project, [_minimal_finding()])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode == 0, result.stdout + result.stderr


# ── replay (full mode) ──────────────────────────────────────────────────────

def test_replay_with_correct_value_passes(project_with_fixture: Path) -> None:
    p = project_with_fixture
    _install_replay_target(p)
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.0,  # median of full sessions.csv
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr


def test_replay_with_wrong_value_fails(project_with_fixture: Path) -> None:
    p = project_with_fixture
    _install_replay_target(p)
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=99.9,  # wrong on purpose
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0
    assert "value mismatch" in result.stdout or "value mismatch" in result.stderr


def test_replay_detects_row_count_drift(project_with_fixture: Path) -> None:
    p = project_with_fixture
    _install_replay_target(p)
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.0,
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["data_contract"]["row_count_after_filter"] = 999  # contract says 999, actual is 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0
    assert "row count" in result.stdout or "row count" in result.stderr


def test_replay_with_dr_filter_changes_value(project_with_fixture: Path) -> None:
    """The whole point: applying DR-001 (mask zero-sentinel) changes the median.
    Without filter: median of [4,4.5,5,3,4,0,4.5,5,3.5,4] = 4.0
    With DR-001 (drop zero): median of 9 values = 4.0 (still)
    With DR-001 (mask to NaN, dropna): median of 9 values = 4.0
    Use mean instead — it differs:
    Without filter: mean = 3.75
    With DR-001: mean = 4.166...
    """
    p = project_with_fixture
    # Install a mean function and a DR-001
    (p / "analysis" / "02_profile.py").write_text("""\
def mean_session_rating(df):
    return float(df["session_rating"].mean())
""")
    (p / "analysis" / "_decisions.py").write_text("""\
import pandas as pd

def DR_001(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["session_rating"] != 0]
""")
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:mean_session_rating",
        value=round((4 + 4.5 + 5 + 3 + 4 + 4.5 + 5 + 3.5 + 4) / 9, 6),  # 4.166...
        measurement_ref="analysis/02_profile.py:mean_session_rating",
    )
    f["data_contract"]["filters"] = ["DR-001"]
    f["data_contract"]["row_count_after_filter"] = 9
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr


def test_replay_with_intra_project_import_succeeds(project_with_fixture: Path) -> None:
    """Regression: validate.py must add project root to sys.path so a profile
    script's 'from analysis._decisions import X' resolves during replay.

    Bug found 2026-05-05: validate would silently log 'ok' while having
    skipped replay due to ImportError. Goodhart on the validator itself.
    """
    p = project_with_fixture
    (p / "analysis" / "_decisions.py").write_text("""\
import pandas as pd

def DR_001(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["session_rating"] != 0]
""")
    (p / "analysis" / "02_profile.py").write_text("""\
from analysis._decisions import DR_001  # noqa: F401 — must resolve during replay

def median_session_rating(df):
    return float(df["session_rating"].median())
""")
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.0,
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "value matches" in result.stdout


def test_replay_fails_loudly_on_import_error(scaffolded_project: Path) -> None:
    """Replay must distinguish 'unimportable' from 'line-ref skip'. Unimportable
    is a hard fail — never silently green.
    """
    p = scaffolded_project
    (p / "analysis" / "broken.py").write_text("import this_does_not_exist\n\ndef fn(df):\n    return 0\n")
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/broken.py:fn",
        value=0,
        measurement_ref="analysis/broken.py:fn",
    )
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0
    assert "import" in result.stdout.lower() or "import" in result.stderr.lower()


def test_boolean_check_type_replays(project_with_fixture: Path) -> None:
    p = project_with_fixture
    (p / "analysis" / "02_profile.py").write_text("""\
def has_zero_sentinel(df):
    return bool((df["session_rating"] == 0).any())
""")
    f = _minimal_finding(
        check_type="boolean",
        code_path="analysis/02_profile.py:has_zero_sentinel",
        value=True,
        measurement_ref="analysis/02_profile.py:has_zero_sentinel",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "value matches" in result.stdout


def test_boolean_check_type_catches_drift(project_with_fixture: Path) -> None:
    p = project_with_fixture
    (p / "analysis" / "02_profile.py").write_text("""\
def has_zero_sentinel(df):
    return bool((df["session_rating"] == 0).any())  # actually True
""")
    f = _minimal_finding(
        check_type="boolean",
        code_path="analysis/02_profile.py:has_zero_sentinel",
        value=False,  # claim is wrong
        measurement_ref="analysis/02_profile.py:has_zero_sentinel",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0
    assert "value mismatch" in result.stdout


def test_manual_check_type_passes_with_warning(scaffolded_project: Path) -> None:
    f = _minimal_finding(
        check_type="manual",
        code_path="analysis/02_profile.py:no_callable_needed",
        measurement_ref="analysis/02_profile.py:no_callable_needed",
    )
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project)
    assert result.returncode == 0
    assert "AUDIT" in result.stdout
    assert "manual" in result.stdout.lower()


def test_matrix_check_type_replays(project_with_fixture: Path) -> None:
    p = project_with_fixture
    (p / "analysis" / "02_profile.py").write_text("""\
def identity_3x3(df):
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
""")
    f = _minimal_finding(
        check_type="matrix",
        code_path="analysis/02_profile.py:identity_3x3",
        measurement_ref="analysis/02_profile.py:identity_3x3",
    )
    f.pop("value", None)
    f.pop("n", None)
    f["matrix"] = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    f["data_contract"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr


def test_matrix_check_type_catches_drift(project_with_fixture: Path) -> None:
    p = project_with_fixture
    (p / "analysis" / "02_profile.py").write_text("""\
def identity_3x3(df):
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
""")
    f = _minimal_finding(
        check_type="matrix",
        code_path="analysis/02_profile.py:identity_3x3",
        measurement_ref="analysis/02_profile.py:identity_3x3",
    )
    f.pop("value", None)
    f.pop("n", None)
    f["matrix"] = [[1.0, 0.0, 0.0], [0.0, 0.99, 0.0], [0.0, 0.0, 1.0]]  # off
    f["data_contract"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0


def test_alpha_suffix_ids_accepted(scaffolded_project: Path) -> None:
    """F-NNN[a-z] is valid for 'corroborating variant' findings (F-010b, F-040b).
    Regression: the v0.2 port surfaced this when noise-solution's real schema
    used F-010b (Spearman corroborating F-010 Pearson) and validate rejected it.
    """
    f1 = _minimal_finding(fid="F-010")
    f2 = _minimal_finding(fid="F-010b")
    write_findings(scaffolded_project, [f1, f2])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode == 0, result.stdout + result.stderr


def test_replay_skips_only_for_line_refs(scaffolded_project: Path) -> None:
    """code_path with :Lstart-Lend is a line reference, not a callable — skip
    is the correct behaviour for these and they should NOT fail replay.
    """
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:L1-L10",
        value=4.0,
        measurement_ref="analysis/02_profile.py:L1-L10",
    )
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project)
    assert result.returncode == 0
    assert "line-ref" in result.stdout


# ── helpers ─────────────────────────────────────────────────────────────────

def _minimal_finding(*, fid: str = "F-001", **overrides) -> dict:
    """Default valid finding, overrideable per test."""
    f = {
        "id": fid,
        "claim": "test claim",
        "check_type": "scalar",
        "code_path": "analysis/02_profile.py:median_session_rating",
        "value": 4.0,
        "n": 10,
        "data_contract": {
            "source": "reference/raw-data/sessions.csv",
            "filters": [],
            "columns": ["session_rating"],
            "row_count_after_filter": 10,
        },
        "caveats": [],
        "counterfactual_tag": "PLAUSIBLE",
        "revision_history": [{"timestamp": "2026-05-05T00:00:00Z", "reason": "test"}],
    }
    f.update(overrides)
    return f


def _install_replay_target(p: Path) -> None:
    """Replace 02_profile.py with a known callable for replay tests."""
    (p / "analysis" / "02_profile.py").write_text("""\
def median_session_rating(df):
    return float(df["session_rating"].median())
""")
