"""0.3.0 grounding & drift: source hashing, per-finding tolerance, schema-lock drift."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from test_validate import _install_replay_target, _minimal_finding, run_validate, write_findings


def _run_in_project(project: Path, code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=project,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(project), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── source hashing (input identity) ──────────────────────────────────────────

def test_replay_fails_on_wrong_source_hash(project_with_fixture: Path) -> None:
    p = project_with_fixture
    _install_replay_target(p)
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.0,
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    f["data_contract"]["source_sha256"] = "deadbeef" * 8  # wrong
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0
    assert "sha256 mismatch" in result.stdout


def test_correct_source_hash_replays(project_with_fixture: Path) -> None:
    p = project_with_fixture
    _install_replay_target(p)
    real = _sha256(p / "reference" / "raw-data" / "sessions.csv")
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.0,
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    f["data_contract"]["source_sha256"] = real
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr


def test_register_stamps_source_hash(project_with_fixture: Path) -> None:
    p = project_with_fixture
    code = """
import sys; sys.path.insert(0, '.')
from analysis._findings import register
register(id='F-001', claim='x', check_type='scalar',
    code_path='analysis/02_profile.py:median_session_rating', value=4.0,
    data_contract={'source':'reference/raw-data/sessions.csv','filters':[],
                   'columns':['session_rating'],'row_count_after_filter':10},
    caveats=[], counterfactual_tag='WEAK')
"""
    res = _run_in_project(p, code)
    assert res.returncode == 0, res.stderr
    findings = json.loads((p / "analysis" / "output" / "findings.json").read_text())
    assert findings[0]["data_contract"]["source_sha256"] == _sha256(
        p / "reference" / "raw-data" / "sessions.csv")


def test_source_hash_disagreement_fails(scaffolded_project: Path) -> None:
    """Two findings on the same source must not disagree on its hash — that
    means they replayed against different snapshots."""
    p = scaffolded_project
    f1 = _minimal_finding(fid="F-001")
    f1["data_contract"]["source_sha256"] = "a" * 64
    f2 = _minimal_finding(fid="F-002")
    f2["data_contract"]["source_sha256"] = "b" * 64
    write_findings(p, [f1, f2])
    result = run_validate(p, "--fast")
    assert result.returncode != 0
    assert "disagree" in result.stdout


def test_unpinned_source_warns_and_is_strict_failure(scaffolded_project: Path) -> None:
    p = scaffolded_project
    write_findings(p, [_minimal_finding()])  # no source_sha256
    result = run_validate(p, "--fast")
    assert result.returncode == 0, result.stdout
    assert "unpinned" in result.stdout
    strict = run_validate(p, "--fast", "--strict")
    assert strict.returncode != 0


# ── per-finding tolerance (the trust knob, kept honest) ──────────────────────

def test_custom_tolerance_widens_match_and_warns(project_with_fixture: Path) -> None:
    p = project_with_fixture
    _install_replay_target(p)  # median 4.0
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.005,  # 5e-3 off — outside the default 1e-6
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    f["tolerance"] = {"abs": 0.01}
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "custom replay tolerance" in result.stdout  # auditable


def test_loose_tolerance_rejected(scaffolded_project: Path) -> None:
    p = scaffolded_project
    f = _minimal_finding(check_type="scalar")
    f["tolerance"] = {"abs": 5}  # exceeds the cap of 1.0
    write_findings(p, [f])
    result = run_validate(p, "--fast")
    assert result.returncode != 0
    assert "too loose" in result.stdout


def test_tolerance_bad_shape_rejected(scaffolded_project: Path) -> None:
    p = scaffolded_project
    f = _minimal_finding(check_type="scalar")
    f["tolerance"] = 0.5  # not an object
    write_findings(p, [f])
    result = run_validate(p, "--fast")
    assert result.returncode != 0


def test_loose_tolerance_cannot_mask_drift(project_with_fixture: Path) -> None:
    """Even at the maximum allowed tolerance, a genuinely wrong value must fail —
    the cap exists precisely so tolerance can't be widened to hide drift."""
    p = project_with_fixture
    _install_replay_target(p)  # median 4.0
    f = _minimal_finding(
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=2.0,  # off by 2.0 ≫ cap 1.0
        measurement_ref="analysis/02_profile.py:median_session_rating",
    )
    f["data_contract"]["row_count_after_filter"] = 10
    f["tolerance"] = {"abs": 1.0}  # the max
    write_findings(p, [f])
    result = run_validate(p)
    assert result.returncode != 0
    assert "value mismatch" in result.stdout


# ── schema-lock drift (opt-in) ───────────────────────────────────────────────

def test_schema_lock_detects_drift(project_with_fixture: Path) -> None:
    p = project_with_fixture
    res = _run_in_project(p, (
        "import sys; sys.path.insert(0, '.')\n"
        "from analysis.schemas import RawSessions, snapshot\n"
        "snapshot(RawSessions, 'reference/raw-data/sessions.csv')\n"
    ))
    assert res.returncode == 0, res.stderr
    assert (p / "analysis" / "output" / "schema-lock.json").exists()

    write_findings(p, [])
    assert run_validate(p).returncode == 0, "conforming data must pass"

    # Push a session_rating out of the schema's [0, 5] range.
    csv = p / "reference" / "raw-data" / "sessions.csv"
    csv.write_text(csv.read_text().replace("S001,4.0", "S001,9.0"))
    result = run_validate(p)
    assert result.returncode != 0
    assert "schema" in result.stdout.lower()


def test_schema_lock_absent_is_noop(project_with_fixture: Path) -> None:
    p = project_with_fixture
    write_findings(p, [])
    result = run_validate(p)
    assert result.returncode == 0
    assert "schema_drift" not in result.stdout  # the check did not run
