"""Smoke tests for the status report generator (analysis/report.py)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_report(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python", "analysis/report.py", *args],
        cwd=project, capture_output=True, text=True,
    )


def report_html(project: Path) -> str:
    return (project / "analysis" / "output" / "report.html").read_text()


def _write_findings(project: Path, findings: list[dict]) -> None:
    (project / "analysis" / "output" / "findings.json").write_text(json.dumps(findings, indent=2))


def _manual_finding() -> dict:
    # `manual` check_type replays trivially (no code/data needed) — good for a smoke test.
    return {
        "id": "F-001",
        "claim": "a documented, audited-by-hand claim",
        "check_type": "manual",
        "code_path": "analysis/02_profile.py:L1-L2",
        "input": {"sources": [{"path": "reference/raw-data/x.csv"}], "columns": ["a"]},
        "reproducibility": {"filters": []},
        "caveats": ["some_caveat: worth knowing"],
        "counterfactual_tag": "PLAUSIBLE",
        "revision_history": [{"timestamp": "2026-01-01T00:00:00Z", "reason": "test"}],
        "decisions": ["DR-001"],
        "addresses": ["A-001"],
    }


def test_report_runs_on_empty_scaffold(scaffolded_project: Path) -> None:
    result = run_report(scaffolded_project)
    assert result.returncode == 0, result.stdout + result.stderr
    html = report_html(scaffolded_project)
    assert "Analysis Status Report" in html
    assert "No findings registered yet." in html
    # self-contained: no external resource fetches
    assert "http://" not in html and "https://" not in html


def test_report_renders_a_finding(scaffolded_project: Path) -> None:
    _write_findings(scaffolded_project, [_manual_finding()])
    result = run_report(scaffolded_project)
    assert result.returncode == 0, result.stdout + result.stderr
    html = report_html(scaffolded_project)
    assert "F-001" in html
    assert "Findings (1)" in html
    assert "manual" in html                       # health chip for a manual finding
    assert "A-001" in html and "DR-001" in html   # the structured link fields surface


def test_report_artifact_mode_is_body_only(scaffolded_project: Path, tmp_path: Path) -> None:
    frag = tmp_path / "frag.html"
    result = run_report(scaffolded_project, "--artifact", str(frag))
    assert result.returncode == 0, result.stdout + result.stderr
    h = frag.read_text()
    assert h.lstrip().startswith("<style>")
    for tag in ("<!doctype", "<html", "<body"):
        assert tag not in h.lower()


def test_report_is_not_gated_on_validate(scaffolded_project: Path) -> None:
    # A drifted finding (bad code_path for a replayable type) must NOT stop the
    # report from rendering — its job is to surface drift, not gate on it.
    bad = _manual_finding()
    bad["check_type"] = "scalar"
    bad["value"] = 1.0
    bad["code_path"] = "analysis/does_not_exist.py:missing"
    bad["reproducibility"]["row_count_after_filter"] = 1
    bad["input"]["sources"] = [{"path": "reference/raw-data/x.csv"}]
    _write_findings(scaffolded_project, [bad])
    result = run_report(scaffolded_project)
    assert result.returncode == 0, result.stdout + result.stderr
    html = report_html(scaffolded_project)
    assert "Out of sync" in html  # the drift is surfaced as an action item
