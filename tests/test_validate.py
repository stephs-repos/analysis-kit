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
    f["reproducibility"]["row_count_after_filter"] = 10
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
    f["reproducibility"]["row_count_after_filter"] = 10
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
    f["reproducibility"]["row_count_after_filter"] = 999  # contract says 999, actual is 10
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
    f["reproducibility"]["filters"] = ["DR-001"]
    f["reproducibility"]["row_count_after_filter"] = 9
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
    f["reproducibility"]["row_count_after_filter"] = 10
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
    f["reproducibility"]["row_count_after_filter"] = 10
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
    f["reproducibility"]["row_count_after_filter"] = 10
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
    f["reproducibility"]["row_count_after_filter"] = 10
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
    f["reproducibility"]["row_count_after_filter"] = 10
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


def test_typed_finding_rejects_line_ref_code_path(scaffolded_project: Path) -> None:
    """A replayable check_type (scalar) with a line-ref code_path must FAIL — a
    value that cannot be re-run is not a verified value. This is the #1 hole:
    previously such a finding printed a green 'REPLAY ok (skipped)' and exit 0.
    """
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:L1-L10",
        value=4.0,
        measurement_ref="analysis/02_profile.py:L1-L10",
    )
    write_findings(scaffolded_project, [f])
    # Fails even in --fast: caught structurally, no code is run.
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "line reference" in result.stdout


def test_bare_code_path_rejected(scaffolded_project: Path) -> None:
    """A code_path with no ':function' suffix must FAIL — it can never replay.
    Previously this was the easiest way to ship an unverifiable number.
    """
    f = _minimal_finding(check_type="scalar", code_path="analysis/02_profile.py", value=999.0)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "code_path" in result.stdout


def test_invalid_code_path_suffix_rejected(scaffolded_project: Path) -> None:
    """A suffix that is neither a function name nor Lstart-Lend must FAIL."""
    f = _minimal_finding(check_type="scalar", code_path="analysis/02_profile.py:123", value=4.0)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "neither a function name" in result.stdout


def test_manual_finding_allows_line_ref(scaffolded_project: Path) -> None:
    """Line refs remain valid for `manual` findings (audit-only, no replay)."""
    f = _minimal_finding(
        check_type="manual",
        code_path="analysis/02_profile.py:L1-L10",
    )
    f.pop("value", None)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "AUDIT" in result.stdout


def test_function_named_like_line_ref_is_callable(project_with_fixture: Path) -> None:
    """Regression: a real function named 'L2_norm' must NOT be misclassified as
    a line reference (the old fn_name[1:2].isdigit() heuristic did exactly that).
    """
    p = project_with_fixture
    (p / "analysis" / "02_profile.py").write_text("""\
def L2_norm(df):
    return float((df["session_rating"] ** 2).sum() ** 0.5)
""")
    import math
    vals = [4, 4.5, 5, 3, 4, 0, 4.5, 5, 3.5, 4]
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:L2_norm",
        value=round(math.sqrt(sum(v * v for v in vals)), 6),
        measurement_ref="analysis/02_profile.py:L2_norm",
    )
    f["reproducibility"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "value matches" in result.stdout


# ── conditional payload enforcement (closes the vacuous-replay hole) ─────────

def test_scalar_missing_value_rejected(scaffolded_project: Path) -> None:
    """A scalar with no `value` must FAIL structurally — otherwise the function
    could return None and None == None would replay green."""
    f = _minimal_finding(check_type="scalar")
    f.pop("value", None)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "value" in result.stdout


def test_scalar_value_zero_is_accepted(scaffolded_project: Path) -> None:
    """A legitimate value of 0 must NOT be rejected by the presence check."""
    f = _minimal_finding(check_type="scalar", value=0)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode == 0, result.stdout + result.stderr


def test_boolean_value_must_be_bool(scaffolded_project: Path) -> None:
    f = _minimal_finding(check_type="boolean", value=1)  # int, not bool
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "bool" in result.stdout


def test_distribution_missing_field_rejected(scaffolded_project: Path) -> None:
    f = _minimal_finding(check_type="distribution")
    f.pop("value", None)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "distribution" in result.stdout


def test_distribution_empty_object_rejected(scaffolded_project: Path) -> None:
    """An empty distribution {} previously replayed vacuously (empty loop → True)."""
    f = _minimal_finding(check_type="distribution")
    f.pop("value", None)
    f["distribution"] = {}
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0


def test_matrix_missing_field_rejected(scaffolded_project: Path) -> None:
    f = _minimal_finding(check_type="matrix")
    f.pop("value", None)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "matrix" in result.stdout


def test_quote_provenance_requires_quote_and_locator(scaffolded_project: Path) -> None:
    f = _minimal_finding(check_type="quote_provenance")
    f.pop("value", None)
    write_findings(scaffolded_project, [f])
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "quote" in result.stdout


# ── replay coverage for previously-untested check_types ──────────────────────

def test_distribution_replays(project_with_fixture: Path) -> None:
    p = project_with_fixture
    (p / "analysis" / "02_profile.py").write_text("""\
def rating_quartiles(df):
    s = df["session_rating"]
    return {"min": float(s.min()), "median": float(s.median()), "max": float(s.max())}
""")
    f = _minimal_finding(
        check_type="distribution",
        code_path="analysis/02_profile.py:rating_quartiles",
        measurement_ref="analysis/02_profile.py:rating_quartiles",
    )
    f.pop("value", None)
    f["distribution"] = {"min": 0.0, "median": 4.0, "max": 5.0}
    f["reproducibility"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "value matches" in result.stdout


def test_distribution_catches_drift(project_with_fixture: Path) -> None:
    p = project_with_fixture
    (p / "analysis" / "02_profile.py").write_text("""\
def rating_quartiles(df):
    s = df["session_rating"]
    return {"min": float(s.min()), "median": float(s.median()), "max": float(s.max())}
""")
    f = _minimal_finding(
        check_type="distribution",
        code_path="analysis/02_profile.py:rating_quartiles",
        measurement_ref="analysis/02_profile.py:rating_quartiles",
    )
    f.pop("value", None)
    f["distribution"] = {"min": 0.0, "median": 3.0, "max": 5.0}  # median is wrong
    f["reproducibility"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0
    assert "value mismatch" in result.stdout


def test_proportion_replays(project_with_fixture: Path) -> None:
    p = project_with_fixture
    (p / "analysis" / "02_profile.py").write_text("""\
def share_five_star(df):
    return float((df["session_rating"] == 5).mean())
""")
    f = _minimal_finding(
        check_type="proportion",
        code_path="analysis/02_profile.py:share_five_star",
        value=0.2,  # 2 of 10 rows are 5.0
        measurement_ref="analysis/02_profile.py:share_five_star",
    )
    f["reproducibility"]["row_count_after_filter"] = 10
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr


def test_quote_provenance_replays_and_catches_missing(scaffolded_project: Path) -> None:
    p = scaffolded_project
    src = p / "reference" / "brief.txt"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("The stakeholder cares most about retention in week one.\n")
    good = _minimal_finding(
        fid="F-001",
        check_type="quote_provenance",
        code_path="analysis/02_profile.py:median_session_rating",
    )
    good.pop("value", None)
    good["quote"] = "retention in week one"
    good["source_locator"] = "reference/brief.txt:L1"
    write_findings(p, [good])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "quote found" in result.stdout

    bad = dict(good)
    bad["quote"] = "a sentence that is not present"
    write_findings(p, [bad])
    result = run_validate(p)
    assert result.returncode != 0
    assert "quote not found" in result.stdout


def test_quote_provenance_path_traversal_blocked(scaffolded_project: Path) -> None:
    """A source_locator escaping the project root must not 'verify' — the claim
    would not be reproducible from repo state."""
    p = scaffolded_project
    secret = p.parent / "outside_secret.txt"
    secret.write_text("retention in week one\n")
    try:
        f = _minimal_finding(check_type="quote_provenance",
                             code_path="analysis/02_profile.py:median_session_rating")
        f.pop("value", None)
        f["quote"] = "retention in week one"
        f["source_locator"] = "../outside_secret.txt:L1"
        write_findings(p, [f])
        result = run_validate(p)
        assert result.returncode != 0
        assert "quote not found" in result.stdout
    finally:
        secret.unlink(missing_ok=True)


# ── tolerance boundary ───────────────────────────────────────────────────────

def test_replay_tolerance_boundary(project_with_fixture: Path) -> None:
    """The numeric tolerance is the trust contract for scalar claims. Pin it:
    a value within 1e-6 replays green; just outside fails. Guards against a
    careless 'make replay less flaky' loosening."""
    p = project_with_fixture
    _install_replay_target(p)  # median = 4.0
    within = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.0000005,  # 5e-7 < 1e-6
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    within["reproducibility"]["row_count_after_filter"] = 10
    write_findings(p, [within])
    assert run_validate(p).returncode == 0

    outside = dict(within)
    outside["value"] = 4.001  # 1e-3 ≫ 1e-6
    write_findings(p, [outside])
    assert run_validate(p).returncode != 0


# ── graceful failure on malformed input (no traceback) ───────────────────────

def test_non_object_entry_fails_gracefully(scaffolded_project: Path) -> None:
    out = scaffolded_project / "analysis" / "output" / "findings.json"
    out.write_text(json.dumps(["not an object"]))
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, result.stderr
    assert "object" in result.stdout


def test_null_fields_fail_gracefully(scaffolded_project: Path) -> None:
    out = scaffolded_project / "analysis" / "output" / "findings.json"
    out.write_text(json.dumps([{"id": None, "claim": None, "code_path": None}]))
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, result.stderr


def test_malformed_json_fails_gracefully(scaffolded_project: Path) -> None:
    out = scaffolded_project / "analysis" / "output" / "findings.json"
    out.write_text("{not valid json")
    result = run_validate(scaffolded_project, "--fast")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, result.stderr


def test_broken_decisions_module_fails_gracefully(project_with_fixture: Path) -> None:
    """A syntax error in _decisions.py must be a clean replay failure, not a
    crash that aborts every other finding's check."""
    p = project_with_fixture
    _install_replay_target(p)
    (p / "analysis" / "_decisions.py").write_text("def DR_001(df):\n    return df[\n")  # syntax error
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.0,
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["reproducibility"]["filters"] = ["DR-001"]
    f["reproducibility"]["row_count_after_filter"] = 9
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, result.stderr
    assert "_decisions" in result.stdout


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
        "input": {
            "sources": [{"path": "reference/raw-data/sessions.csv"}],
            "columns": ["session_rating"],
        },
        "reproducibility": {
            "filters": [],
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


# ── decisions ↔ caveats sync ────────────────────────────────────────────────

_FILLED_CAVEATS = """\
---
name: Data quality caveats
---

### A caveat

- **Rule:** do a thing before aggregating
- **How to apply:** {how}
"""


def _fill_caveats(p: Path, *, dr_ref: str | None) -> None:
    """Overwrite the register with resolved content (no MUST_CUSTOMIZE marker)."""
    how = dr_ref if dr_ref else "operational only"
    (p / "memory" / "data_quality_caveats.md").write_text(_FILLED_CAVEATS.format(how=how))


def _add_dr_function(p: Path, dr: str = "DR_001") -> None:
    f = p / "analysis" / "_decisions.py"
    f.write_text(f.read_text() + f"\n\ndef {dr}(df):\n    return df\n")


def test_sync_dormant_while_caveats_unfilled(scaffolded_project: Path) -> None:
    # Fresh scaffold still carries the MUST_CUSTOMIZE marker → check skips even
    # though a DR function exists and DECISIONS ships an example DR-001 entry.
    _add_dr_function(scaffolded_project)
    result = run_validate(scaffolded_project)  # full mode
    assert result.returncode == 0, result.stdout + result.stderr
    assert "decisions_caveats:sync" not in result.stdout


def test_sync_flags_active_dr_not_in_register(scaffolded_project: Path) -> None:
    _fill_caveats(scaffolded_project, dr_ref=None)   # resolved, but no DR ref
    _add_dr_function(scaffolded_project)             # DR-001 now implemented + active
    result = run_validate(scaffolded_project)        # full mode = commit gate
    assert result.returncode != 0
    assert "DR-001 is active/implemented but not referenced" in result.stdout


def test_sync_passes_when_dr_referenced(scaffolded_project: Path) -> None:
    _fill_caveats(scaffolded_project, dr_ref="DR-001")
    _add_dr_function(scaffolded_project)
    result = run_validate(scaffolded_project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS  decisions_caveats:sync" in result.stdout


def test_sync_warns_not_fails_in_fast_mode(scaffolded_project: Path) -> None:
    _fill_caveats(scaffolded_project, dr_ref=None)
    _add_dr_function(scaffolded_project)
    result = run_validate(scaffolded_project, "--fast")   # Stop-hook mode = nudge
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARN  decisions_caveats:sync" in result.stdout


# ── aggregate freshness (materialised intermediates) ─────────────────────────

def _build_agg_with_manifest(project: Path, *, source: str = "reference/raw-data/big.csv",
                             dr_set: tuple[str, ...] = ("DR-001",)) -> Path:
    """Write a tiny derived table + its raw source, then a manifest via the
    project's own _provenance.write_manifest (exercises writer + reader together)."""
    out = project / "analysis" / "output" / "agg.csv"
    out.write_text("date,n\n2024-01-01,5\n")
    src = project / source
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("raw,data\n1,2\n")
    r = subprocess.run(
        ["python", "-c",
         "from analysis._provenance import write_manifest; "
         f"write_manifest(output='analysis/output/agg.csv', sources=['{source}'], dr_set={list(dr_set)})"],
        cwd=project, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    return src


def test_freshness_noop_without_manifest(scaffolded_project: Path) -> None:
    # Fresh scaffold has no manifest → check is silent, not a spurious pass/fail.
    result = run_validate(scaffolded_project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "aggregate:freshness" not in result.stdout


def test_freshness_passes_when_fresh(scaffolded_project: Path) -> None:
    _build_agg_with_manifest(scaffolded_project)
    result = run_validate(scaffolded_project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS  aggregate:freshness" in result.stdout


def test_freshness_fails_on_source_change(scaffolded_project: Path) -> None:
    src = _build_agg_with_manifest(scaffolded_project)
    src.write_text("raw,data\n9,9\n")                 # raw source mutated after build
    result = run_validate(scaffolded_project)
    assert result.returncode != 0
    assert "changed since build" in result.stdout


def test_freshness_warns_not_fails_when_source_absent(scaffolded_project: Path) -> None:
    src = _build_agg_with_manifest(scaffolded_project)
    src.unlink()                                       # raw distributed out-of-band
    result = run_validate(scaffolded_project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "cannot verify" in result.stdout


def test_freshness_fails_on_output_edit(scaffolded_project: Path) -> None:
    _build_agg_with_manifest(scaffolded_project)
    (scaffolded_project / "analysis" / "output" / "agg.csv").write_text("date,n\n2024-01-01,6\n")
    result = run_validate(scaffolded_project)
    assert result.returncode != 0
    assert "changed since build" in result.stdout


def test_freshness_fails_on_dr_change(scaffolded_project: Path) -> None:
    _build_agg_with_manifest(scaffolded_project)
    dec = scaffolded_project / "analysis" / "_decisions.py"
    dec.write_text(dec.read_text() + "\n# a rule's logic changed\n")
    result = run_validate(scaffolded_project)
    assert result.returncode != 0
    assert "DR definition in _decisions.py changed" in result.stdout
