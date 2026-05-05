"""
_findings.py — registration helper for findings.json.

Use this to add or update findings programmatically. It enforces the schema
locally (rather than waiting for validate.py to fail) and writes back atomically.

Usage:

    from analysis._findings import register, update

    register(
        id="F-001",
        claim="median session rating is 4.2 (n=312)",
        check_type="scalar",
        code_path="analysis/02_profile.py:median_session_rating",
        value=4.2,
        n=312,
        data_contract={
            "source": "reference/raw-data/sessions.csv",
            "filters": ["DR-001", "DR-003"],
            "columns": ["session_rating"],
            "row_count_after_filter": 312,
        },
        caveats=["zero_sentinel_masked"],
        counterfactual_tag="OBSERVED",
        measurement_ref="analysis/02_profile.py:L120-L145",
        reason="initial entry",
    )
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "analysis" / "output" / "findings.json"

VALID_CHECK_TYPES = {"scalar", "distribution", "matrix", "quote_provenance", "proportion", "rate"}
VALID_TAGS = {"OBSERVED", "PLAUSIBLE", "WEAK"}


def _load() -> list[dict[str, Any]]:
    if not FINDINGS.exists():
        FINDINGS.parent.mkdir(parents=True, exist_ok=True)
        return []
    return json.loads(FINDINGS.read_text())


def _atomic_write(data: list[dict]) -> None:
    FINDINGS.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".findings.", suffix=".json", dir=FINDINGS.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=False)
            f.write("\n")
        os.replace(tmp, FINDINGS)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate(f: dict[str, Any]) -> None:
    required = ["id", "claim", "check_type", "code_path", "data_contract", "caveats", "counterfactual_tag"]
    for k in required:
        if k not in f:
            raise ValueError(f"missing required field {k!r}")
    if f["check_type"] not in VALID_CHECK_TYPES:
        raise ValueError(f"unknown check_type {f['check_type']!r}")
    if f["counterfactual_tag"] not in VALID_TAGS:
        raise ValueError(f"unknown counterfactual_tag {f['counterfactual_tag']!r}")
    if f["counterfactual_tag"] == "OBSERVED" and not f.get("measurement_ref"):
        raise ValueError("OBSERVED tag requires measurement_ref")
    dc = f["data_contract"]
    for k in ("source", "filters", "columns", "row_count_after_filter"):
        if k not in dc:
            raise ValueError(f"data_contract missing {k!r}")


def register(*, reason: str = "initial entry", **fields: Any) -> dict[str, Any]:
    """Add a new finding. Raises if id already exists; use update() instead."""
    findings = _load()
    fid = fields.get("id")
    if fid is None:
        raise ValueError("id is required")
    if any(x.get("id") == fid for x in findings):
        raise ValueError(f"finding {fid} already exists; use update()")

    fields.setdefault("caveats", [])
    fields["revision_history"] = [{"timestamp": _now(), "reason": reason}]
    _validate(fields)
    findings.append(fields)
    _atomic_write(findings)
    return fields


def update(fid: str, *, reason: str, **changes: Any) -> dict[str, Any]:
    """Update an existing finding; appends to revision_history."""
    findings = _load()
    for i, f in enumerate(findings):
        if f.get("id") == fid:
            f.update(changes)
            f.setdefault("revision_history", []).append({"timestamp": _now(), "reason": reason})
            _validate(f)
            findings[i] = f
            _atomic_write(findings)
            return f
    raise KeyError(f"finding {fid} not found")


def next_id() -> str:
    """Return the next available F-NNN id."""
    findings = _load()
    if not findings:
        return "F-001"
    highest = max(int(f["id"].split("-")[1]) for f in findings if f.get("id"))
    return f"F-{highest + 1:03d}"
