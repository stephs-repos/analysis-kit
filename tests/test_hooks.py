"""Test the Claude Code hooks the kit scaffolds — the deterministic enforcement
surface. These exercise the actual shipped scripts with crafted hook payloads.

Hook I/O protocol (Claude Code spec) under test:
  - PreToolUse / Stop: exit 0 = allow, exit 2 = block (stderr → Claude)
  - PostToolUse nudge: exit 0 + hookSpecificOutput.additionalContext (→ Claude)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _run_hook(project: Path, name: str, payload: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        [str(project / ".claude" / "hooks" / name)],
        input=payload,
        cwd=project,
        capture_output=True,
        text=True,
        env=env,
    )


def _bash_payload(command: str) -> str:
    return json.dumps({"tool_input": {"command": command}})


def _edit_payload(file_path: str) -> str:
    return json.dumps({"tool_input": {"file_path": file_path}})


def _make_red(project: Path) -> None:
    (project / "analysis" / "output" / "findings.json").write_text('[{"id": "F-001"}]')


jq_required = pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed")


# ── block-unvalidated-commit.sh (PreToolUse on Bash) ─────────────────────────

@jq_required
def test_commit_allowed_when_validate_green(scaffolded_project: Path) -> None:
    # Fresh scaffold: findings.json is [] → validate green → commit allowed.
    r = _run_hook(scaffolded_project, "block-unvalidated-commit.sh", _bash_payload("git commit -m x"))
    assert r.returncode == 0, r.stdout + r.stderr


@jq_required
def test_commit_blocked_when_validate_red(scaffolded_project: Path) -> None:
    _make_red(scaffolded_project)
    r = _run_hook(scaffolded_project, "block-unvalidated-commit.sh", _bash_payload("git commit -m x"))
    assert r.returncode == 2
    assert "BLOCKED" in r.stderr  # the reason reaches Claude on stderr (exit 2)


@jq_required
@pytest.mark.parametrize("command", [
    "git commit -m x",
    "git -C /somewhere commit -m x",     # -C flag form Claude emits naturally
    "git -c user.name=x commit -m x",    # -c flag form
    "git  commit -m x",                  # collapsed whitespace
    "cd sub && git commit -m x",         # after &&
])
def test_commit_forms_are_detected(scaffolded_project: Path, command: str) -> None:
    _make_red(scaffolded_project)
    r = _run_hook(scaffolded_project, "block-unvalidated-commit.sh", _bash_payload(command))
    assert r.returncode == 2, f"{command!r} should have been detected as a commit"


@jq_required
@pytest.mark.parametrize("command", [
    'grep "git commit" docs/',           # mentions the phrase, isn't a commit
    "git log --grep=commit",             # git, but not a commit
    "git commit-tree abc",               # commit-tree is not commit
    "ls -la",                            # unrelated
])
def test_non_commits_allowed_even_when_red(scaffolded_project: Path, command: str) -> None:
    _make_red(scaffolded_project)
    r = _run_hook(scaffolded_project, "block-unvalidated-commit.sh", _bash_payload(command))
    assert r.returncode == 0, f"{command!r} should not be treated as a commit"


# ── validate-on-stop.sh (Stop) ───────────────────────────────────────────────

@jq_required
def test_stop_allowed_when_green(scaffolded_project: Path) -> None:
    r = _run_hook(scaffolded_project, "validate-on-stop.sh", json.dumps({"stop_hook_active": False}))
    assert r.returncode == 0, r.stdout + r.stderr


@jq_required
def test_stop_blocked_when_red(scaffolded_project: Path) -> None:
    _make_red(scaffolded_project)
    r = _run_hook(scaffolded_project, "validate-on-stop.sh", json.dumps({"stop_hook_active": False}))
    assert r.returncode == 2
    assert "red" in r.stderr.lower()


@jq_required
def test_stop_yields_on_active_guard_to_avoid_loop(scaffolded_project: Path) -> None:
    """Even with red findings, stop_hook_active=true must yield (exit 0) — this is
    the guard against an infinite stop → block → stop loop."""
    _make_red(scaffolded_project)
    r = _run_hook(scaffolded_project, "validate-on-stop.sh", json.dumps({"stop_hook_active": True}))
    assert r.returncode == 0, r.stdout + r.stderr


# ── findings-coverage-on-edit.sh (PostToolUse) ───────────────────────────────

@jq_required
def test_edit_nudge_uses_additional_context_channel(scaffolded_project: Path) -> None:
    """The nudge must reach Claude via hookSpecificOutput.additionalContext —
    plain stdout on a PostToolUse exit-0 only shows in the transcript."""
    r = _run_hook(scaffolded_project, "findings-coverage-on-edit.sh", _edit_payload("analysis/02_profile.py"))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "validate.py" in out["hookSpecificOutput"]["additionalContext"]


@jq_required
def test_edit_nudge_also_fires_for_decisions_module(scaffolded_project: Path) -> None:
    r = _run_hook(scaffolded_project, "findings-coverage-on-edit.sh", _edit_payload("analysis/_decisions.py"))
    assert r.returncode == 0
    assert json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


@jq_required
@pytest.mark.parametrize("file_path", [
    "reanalysis/01_x.py",   # ends in "analysis/" but isn't analysis/ — must not fire
    "README.md",            # not a compute script
    "analysis/validate.py", # infra, not a numbered step or _decisions
])
def test_edit_nudge_does_not_fire_for_unrelated_files(scaffolded_project: Path, file_path: str) -> None:
    r = _run_hook(scaffolded_project, "findings-coverage-on-edit.sh", _edit_payload(file_path))
    assert r.returncode == 0
    assert r.stdout.strip() == "", f"{file_path!r} should not trigger the nudge"


# ── all hooks are wired and executable ───────────────────────────────────────

def test_settings_wires_all_three_hooks(scaffolded_project: Path) -> None:
    settings = json.loads((scaffolded_project / ".claude" / "settings.json").read_text())
    hooks = settings["hooks"]
    # Commands reference the project dir, not a fragile relative path.
    for event in ("Stop", "PreToolUse", "PostToolUse"):
        cmd = hooks[event][0]["hooks"][0]["command"]
        assert "CLAUDE_PROJECT_DIR" in cmd, f"{event} hook should use $CLAUDE_PROJECT_DIR"
        assert hooks[event][0]["hooks"][0]["timeout"] > 0
    # The edit matcher covers all the edit tools, not just Edit|Write.
    assert hooks["PostToolUse"][0]["matcher"] == "Edit|MultiEdit|Write|NotebookEdit"
