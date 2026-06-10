"""Test the _findings.py registration helper."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_in_project(project: Path, code: str) -> subprocess.CompletedProcess:
    """Execute Python code with the project as cwd and on sys.path."""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=project,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(project), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def test_register_creates_finding(scaffolded_project: Path) -> None:
    p = scaffolded_project
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import register
register(
    id='F-001',
    claim='test',
    check_type='scalar',
    code_path='analysis/02_profile.py:median_session_rating',
    value=4.0,
    n=10,
    data_contract={'source': 'x.csv', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 10},
    caveats=[],
    counterfactual_tag='PLAUSIBLE',
)
"""
    result = _run_in_project(p, code)
    assert result.returncode == 0, result.stderr
    findings = json.loads((p / "analysis" / "output" / "findings.json").read_text())
    assert len(findings) == 1
    assert findings[0]["id"] == "F-001"
    assert findings[0]["revision_history"][0]["reason"] == "initial entry"


def test_register_observed_requires_measurement_ref(scaffolded_project: Path) -> None:
    p = scaffolded_project
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import register
register(
    id='F-001',
    claim='test',
    check_type='scalar',
    code_path='analysis/02_profile.py:fn',
    value=4.0,
    data_contract={'source': 'x.csv', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 1},
    caveats=[],
    counterfactual_tag='OBSERVED',
)
"""
    result = _run_in_project(p, code)
    assert result.returncode != 0
    assert "OBSERVED" in result.stderr and "measurement_ref" in result.stderr


def test_next_id_increments(scaffolded_project: Path) -> None:
    p = scaffolded_project
    # Pre-seed
    (p / "analysis" / "output" / "findings.json").write_text(json.dumps([
        {"id": "F-001", "claim": "x", "check_type": "scalar", "code_path": "a:b",
         "data_contract": {"source": "x", "filters": [], "columns": [], "row_count_after_filter": 0},
         "caveats": [], "counterfactual_tag": "WEAK",
         "revision_history": [{"timestamp": "x", "reason": "x"}]},
        {"id": "F-002", "claim": "x", "check_type": "scalar", "code_path": "a:b",
         "data_contract": {"source": "x", "filters": [], "columns": [], "row_count_after_filter": 0},
         "caveats": [], "counterfactual_tag": "WEAK",
         "revision_history": [{"timestamp": "x", "reason": "x"}]},
    ]))
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import next_id
print(next_id())
"""
    result = _run_in_project(p, code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "F-003"


def test_register_accepts_boolean_and_manual(scaffolded_project: Path) -> None:
    """0.2.0 added boolean + manual check_types; the helper must accept them
    (it shipped 0.2.1 still rejecting them — the headline types were unusable
    through the sanctioned path)."""
    p = scaffolded_project
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import register
register(
    id='F-001', claim='zero sentinel present', check_type='boolean',
    code_path='analysis/02_profile.py:has_zero', value=True,
    data_contract={'source': 'x.csv', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 10},
    caveats=[], counterfactual_tag='OBSERVED', measurement_ref='analysis/02_profile.py:has_zero',
)
register(
    id='F-002', claim='qualitative judgement', check_type='manual',
    code_path='analysis/02_profile.py:L1-L5',
    data_contract={'source': 'x.csv', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 10},
    caveats=[], counterfactual_tag='WEAK',
)
"""
    result = _run_in_project(p, code)
    assert result.returncode == 0, result.stderr
    findings = json.loads((p / "analysis" / "output" / "findings.json").read_text())
    assert {f["check_type"] for f in findings} == {"boolean", "manual"}


def test_register_rejects_bare_code_path(scaffolded_project: Path) -> None:
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import register
register(
    id='F-001', claim='x', check_type='scalar',
    code_path='analysis/02_profile.py', value=4.0,
    data_contract={'source': 'x.csv', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 1},
    caveats=[], counterfactual_tag='WEAK',
)
"""
    result = _run_in_project(scaffolded_project, code)
    assert result.returncode != 0
    assert "code_path" in result.stderr


def test_register_rejects_line_ref_for_scalar(scaffolded_project: Path) -> None:
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import register
register(
    id='F-001', claim='x', check_type='scalar',
    code_path='analysis/02_profile.py:L1-L10', value=4.0,
    data_contract={'source': 'x.csv', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 1},
    caveats=[], counterfactual_tag='WEAK',
)
"""
    result = _run_in_project(scaffolded_project, code)
    assert result.returncode != 0
    assert "line reference" in result.stderr


def test_register_rejects_missing_value(scaffolded_project: Path) -> None:
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import register
register(
    id='F-001', claim='x', check_type='scalar',
    code_path='analysis/02_profile.py:fn',
    data_contract={'source': 'x.csv', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 1},
    caveats=[], counterfactual_tag='WEAK',
)
"""
    result = _run_in_project(scaffolded_project, code)
    assert result.returncode != 0
    assert "value" in result.stderr


def test_register_rejects_nan_value(scaffolded_project: Path) -> None:
    """A NaN value (e.g. a median over a fully-filtered column) must be rejected
    at registration — it is invalid JSON and can never replay."""
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import register
register(
    id='F-001', claim='x', check_type='scalar',
    code_path='analysis/02_profile.py:fn', value=float('nan'),
    data_contract={'source': 'x.csv', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 1},
    caveats=[], counterfactual_tag='WEAK',
)
"""
    result = _run_in_project(scaffolded_project, code)
    assert result.returncode != 0
    assert "finite" in result.stderr


def test_update_appends_revision_history(scaffolded_project: Path) -> None:
    p = scaffolded_project
    code = """
import sys
sys.path.insert(0, '.')
from analysis._findings import register, update
register(
    id='F-001', claim='v1', check_type='scalar',
    code_path='analysis/02_profile.py:fn', value=1.0,
    data_contract={'source': 'x', 'filters': [], 'columns': ['c'], 'row_count_after_filter': 1},
    caveats=[], counterfactual_tag='WEAK',
)
update('F-001', reason='value corrected', value=2.0, claim='v2')
"""
    result = _run_in_project(p, code)
    assert result.returncode == 0, result.stderr
    findings = json.loads((p / "analysis" / "output" / "findings.json").read_text())
    assert findings[0]["claim"] == "v2"
    assert findings[0]["value"] == 2.0
    assert len(findings[0]["revision_history"]) == 2
    assert findings[0]["revision_history"][1]["reason"] == "value corrected"
