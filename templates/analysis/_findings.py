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
        input={
            "sources": [{"path": "reference/raw-data/sessions.csv"}],
            "columns": ["session_rating"],
        },
        reproducibility={
            "filters": ["DR-001", "DR-003"],
            "row_count_after_filter": 312,
        },
        caveats=["zero_sentinel_masked"],
        counterfactual_tag="OBSERVED",
        measurement_ref="analysis/02_profile.py:L120-L145",
        reason="initial entry",
    )

register() stamps the sha256 of each source automatically when the file is
present, so you don't write it by hand.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "analysis" / "output" / "findings.json"

# Keep this set in lockstep with validate.py's VALID_CHECK_TYPES — the helper
# must not accept a check_type the validator rejects (or vice versa).
VALID_CHECK_TYPES = {
    "scalar", "distribution", "matrix", "quote_provenance",
    "proportion", "rate", "boolean", "manual",
}
VALID_TAGS = {"OBSERVED", "PLAUSIBLE", "WEAK"}
REPLAYABLE_TYPES = {"scalar", "proportion", "rate", "boolean", "distribution", "matrix"}


def _suffix_kind(suffix: str) -> str:
    """Classify a code_path suffix: 'callable', 'line_ref', or 'invalid'.

    Mirrors validate.py — a callable is a Python identifier, a line_ref is
    'Lstart-Lend', everything else is invalid.
    """
    if re.fullmatch(r"L\d+(-L?\d+)?", suffix):
        return "line_ref"
    if suffix.isidentifier():
        return "callable"
    return "invalid"


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
            # allow_nan=False: NaN/Infinity are not valid JSON and break jq, the
            # bash hooks, and any non-Python reader. A NaN value also can never
            # replay (math.isclose(nan, nan) is False), so reject it at the source.
            json.dump(data, f, indent=2, sort_keys=False, allow_nan=False)
            f.write("\n")
        os.replace(tmp, FINDINGS)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _stamp_source_hash(f: dict[str, Any]) -> None:
    """Pin the content hash of each input source so drift is detectable later.
    No-op for a source already pinned or whose file isn't present yet."""
    inp = f.get("input")
    if not isinstance(inp, dict):
        return
    for s in inp.get("sources", []):
        if not isinstance(s, dict) or not isinstance(s.get("path"), str) or s.get("sha256"):
            continue
        p = ROOT / s["path"]
        if p.exists() and p.is_file():
            s["sha256"] = _file_sha256(p)


def _validate(f: dict[str, Any]) -> None:
    required = ["id", "claim", "check_type", "code_path", "input", "reproducibility", "caveats", "counterfactual_tag"]
    for k in required:
        if k not in f:
            raise ValueError(f"missing required field {k!r}")
    ct = f["check_type"]
    if ct not in VALID_CHECK_TYPES:
        raise ValueError(f"unknown check_type {ct!r}")
    if f["counterfactual_tag"] not in VALID_TAGS:
        raise ValueError(f"unknown counterfactual_tag {f['counterfactual_tag']!r}")
    if f["counterfactual_tag"] == "OBSERVED" and not f.get("measurement_ref"):
        raise ValueError("OBSERVED tag requires measurement_ref")

    # code_path form: must be 'file.py:function' or 'file.py:Lstart-Lend', and a
    # replayable check_type must name a runnable function (not a line reference) —
    # otherwise its value can never be verified.
    cp = f.get("code_path") or ""
    if ":" not in cp:
        raise ValueError("code_path must be 'file.py:function' or 'file.py:Lstart-Lend'")
    suffix = cp.rsplit(":", 1)[1]
    kind = _suffix_kind(suffix)
    if kind == "invalid":
        raise ValueError(f"code_path suffix {suffix!r} is neither a function name nor Lstart-Lend")
    if kind == "line_ref" and ct in REPLAYABLE_TYPES:
        raise ValueError(f"{ct} needs a runnable function in code_path, not a line reference")

    # conditional payload — the fields that make a finding replayable
    if ct in {"scalar", "proportion", "rate"} and f.get("value") is None:
        raise ValueError(f"{ct} finding requires a non-null 'value'")
    if ct == "boolean" and not isinstance(f.get("value"), bool):
        raise ValueError("boolean finding requires a bool 'value'")
    if ct == "distribution" and not (isinstance(f.get("distribution"), dict) and f.get("distribution")):
        raise ValueError("distribution finding requires a non-empty 'distribution' object")
    if ct == "matrix" and not (isinstance(f.get("matrix"), list) and f.get("matrix")):
        raise ValueError("matrix finding requires a non-empty 'matrix' list")
    if ct == "quote_provenance" and (not f.get("quote") or not f.get("source_locator")):
        raise ValueError("quote_provenance finding requires 'quote' and 'source_locator'")

    # numeric values must be finite (NaN/Inf are invalid JSON and never replay)
    v = f.get("value")
    if isinstance(v, float) and not math.isfinite(v):
        raise ValueError("value must be finite (no NaN/Inf)")

    inp = f["input"]
    if not isinstance(inp, dict):
        raise ValueError("input must be an object")
    if "columns" not in inp:
        raise ValueError("input missing 'columns'")
    sources = inp.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("input.sources must be a non-empty list of {path, sha256}")
    for s in sources:
        if not isinstance(s, dict) or not isinstance(s.get("path"), str) or not s.get("path"):
            raise ValueError("each input source needs a string 'path'")
    if ct in REPLAYABLE_TYPES and len(sources) != 1:
        raise ValueError(f"a replayable {ct} finding needs exactly one input source; "
                         "declare multi-source findings as check_type 'manual'")

    r = f["reproducibility"]
    if not isinstance(r, dict):
        raise ValueError("reproducibility must be an object")
    if not isinstance(r.get("filters"), list):
        raise ValueError("reproducibility.filters must be a list")
    if ct in REPLAYABLE_TYPES and "row_count_after_filter" not in r:
        raise ValueError("reproducibility missing 'row_count_after_filter'")


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
    _stamp_source_hash(fields)
    _validate(fields)
    findings.append(fields)
    _atomic_write(findings)
    return fields


def register_computed(*, reason: str = "initial entry", **fields: Any) -> dict[str, Any]:
    """Like register(), but the stored value is COMPUTED by running code_path on
    the declared source — the operator cannot supply a number divorced from the
    code that supposedly produced it. This closes the 'store a plausible value,
    point at unrelated code' gap at the source.

    Only for replayable numeric check_types (scalar / proportion / rate /
    boolean / distribution / matrix). For quote_provenance and manual, use
    register(). Any `value`/`distribution`/`matrix` passed in is ignored and
    replaced with the executed result; `row_count_after_filter` is set to the
    actual post-filter count.
    """
    ct = fields.get("check_type")
    if ct not in REPLAYABLE_TYPES:
        raise ValueError(f"register_computed is only for replayable numeric types, not {ct!r}")
    code_path = fields.get("code_path") or ""
    inp = fields.get("input")
    sources = inp.get("sources") if isinstance(inp, dict) else None
    if not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict):
        raise ValueError("register_computed requires input.sources with exactly one {path} source")
    source_path = sources[0].get("path")
    if not isinstance(source_path, str):
        raise ValueError("input.sources[0] needs a string 'path'")
    repro = fields.setdefault("reproducibility", {})
    repro.setdefault("filters", [])

    # Reuse the validator's own import/replay internals so "computed" means
    # exactly what validate.py will later re-run.
    from analysis.validate import _import_callable, _apply_filters, _import_decisions
    import pandas as pd

    fn, err = _import_callable(code_path)
    if fn is None:
        raise ValueError(f"cannot run code_path {code_path!r}: {err}")
    src = ROOT / source_path
    if not src.exists():
        raise FileNotFoundError(f"source {source_path} not found — cannot compute value")
    df = pd.read_csv(src) if src.suffix == ".csv" else pd.read_excel(src)
    df = _apply_filters(df, repro.get("filters", []), _import_decisions())
    repro["row_count_after_filter"] = len(df)
    result = fn(df)

    # Stamp the computed result, coercing to JSON-native types (numpy scalars
    # are not JSON-serializable).
    if ct in {"scalar", "proportion", "rate"}:
        fields["value"] = float(result)
    elif ct == "boolean":
        fields["value"] = bool(result)
    elif ct == "distribution":
        fields["distribution"] = {k: float(v) for k, v in dict(result).items()}
    elif ct == "matrix":
        fields["matrix"] = [[float(x) for x in row] for row in result]

    inp.setdefault("columns", [])
    return register(reason=reason, **fields)


def update(fid: str, *, reason: str, **changes: Any) -> dict[str, Any]:
    """Update an existing finding; appends to revision_history."""
    findings = _load()
    for i, f in enumerate(findings):
        if f.get("id") == fid:
            f.update(changes)
            # If input was touched, drop any stale per-source hashes so they
            # re-pin to the current files.
            if "input" in changes and isinstance(f.get("input"), dict):
                for s in f["input"].get("sources", []):
                    if isinstance(s, dict):
                        s.pop("sha256", None)
            f.setdefault("revision_history", []).append({"timestamp": _now(), "reason": reason})
            _stamp_source_hash(f)
            _validate(f)
            findings[i] = f
            _atomic_write(findings)
            return f
    raise KeyError(f"finding {fid} not found")


def next_id() -> str:
    """Return the next available F-NNN id (alpha suffixes ignored when ranking)."""
    import re as _re
    findings = _load()
    if not findings:
        return "F-001"
    nums = [int(_re.match(r"^F-(\d+)", f["id"]).group(1))
            for f in findings if f.get("id") and _re.match(r"^F-\d", f["id"])]
    return f"F-{max(nums) + 1:03d}"
