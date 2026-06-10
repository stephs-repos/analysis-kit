"""
validate.py — exit code is the trust contract.

Every quantitative claim in findings.json must replay green. Two modes:

  python analysis/validate.py --fast    schema + structural checks only (~1s)
  python analysis/validate.py           full mode: replay every finding's data_contract

Exit 0 = trustworthy. Exit non-zero = stop, fix, do not ship.

This file is shipped by analysis-kit. Project-specific checks live below the
PROJECT-SPECIFIC marker. Don't edit core dispatcher logic — fix it upstream
in analysis-kit and migrate.

Framework version: 0.3.0
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "analysis" / "output" / "findings.json"
DECISIONS_MOD = ROOT / "analysis" / "_decisions.py"
TRUST_MEMO = ROOT / "live-docs" / "TRUST_MEMO.md"
MANIFEST = ROOT / "analysis-kit.json"

VALID_CHECK_TYPES = {
    "scalar", "distribution", "matrix", "quote_provenance",
    "proportion", "rate", "boolean", "manual",
}
VALID_TAGS = {"OBSERVED", "PLAUSIBLE", "WEAK"}

# check_types whose stored value is auto-verified by re-running code. These
# REQUIRE a runnable callable in code_path — a line reference cannot replay a
# value, so allowing it would let a finding silently skip verification.
REPLAYABLE_TYPES = {"scalar", "proportion", "rate", "boolean", "distribution", "matrix"}

failures: list[tuple[str, str]] = []
warnings_: list[tuple[str, str]] = []


def fail(name: str, msg: str) -> None:
    failures.append((name, msg))
    print(f"FAIL  {name}: {msg}")


def warn(name: str, msg: str) -> None:
    warnings_.append((name, msg))
    print(f"WARN  {name}: {msg}")


def ok(name: str) -> None:
    print(f"PASS  {name}")


def load_findings() -> list[dict[str, Any]]:
    if not FINDINGS.exists():
        fail("findings.json:exists", f"{FINDINGS} not found — run analysis/02_profile.py")
        return []
    try:
        data = json.loads(FINDINGS.read_text())
    except json.JSONDecodeError as e:
        fail("findings.json:parses", str(e))
        return []
    if not isinstance(data, list):
        fail("findings.json:shape", "expected a top-level array")
        return []
    if not all(isinstance(x, dict) for x in data):
        fail("findings.json:shape", "every finding must be a JSON object")
        return []
    return data


# ─── code_path helpers ──────────────────────────────────────────────────────

def _suffix_kind(suffix: str) -> str:
    """Classify a code_path suffix.

    'callable'  → a Python identifier (a runnable function), e.g. 'median_rating'
    'line_ref'  → 'Lstart-Lend' line reference, e.g. 'L120-L145' (not runnable)
    'invalid'   → anything else, e.g. '123', 'foo-bar', 'L'
    """
    if re.fullmatch(r"L\d+(-L?\d+)?", suffix):
        return "line_ref"
    if suffix.isidentifier():
        return "callable"
    return "invalid"


# ─── structural checks (fast mode) ──────────────────────────────────────────

def check_ids_unique(findings: list[dict]) -> None:
    seen: set[str] = set()
    for f in findings:
        fid = f.get("id")
        if not fid:
            claim = f.get("claim") or "<no claim>"
            fail("ids:present", f"finding missing id: {str(claim)[:60]}")
            continue
        # F-NNN with optional alpha suffix for corroborating variants (F-010b, F-040b)
        if not re.match(r"^F-\d{3,}[a-z]?$", fid):
            fail("ids:format", f"{fid} does not match F-NNN[a-z]")
        if fid in seen:
            fail("ids:unique", f"duplicate id {fid}")
        seen.add(fid)
    if seen and not failures:
        ok("ids:unique+format")


def check_required_fields(findings: list[dict]) -> None:
    required = ["id", "claim", "check_type", "code_path", "data_contract", "caveats", "counterfactual_tag", "revision_history"]
    for f in findings:
        for field in required:
            if field not in f:
                fail("schema:required", f"{f.get('id', '?')} missing required field {field!r}")
    if not any(n.startswith("schema:required") for n, _ in failures):
        ok("schema:required")


def check_check_types(findings: list[dict]) -> None:
    for f in findings:
        ct = f.get("check_type")
        if ct not in VALID_CHECK_TYPES:
            fail("check_type:valid", f"{f.get('id')}: unknown check_type {ct!r}")
    if not any(n.startswith("check_type") for n, _ in failures):
        ok("check_type:valid")


def check_conditional_fields(findings: list[dict]) -> None:
    """Enforce the per-check_type payload that makes a finding replayable.

    Without this, a 'scalar' with no `value` or a 'distribution' with an empty
    `distribution` object would pass replay vacuously (None == None, or an empty
    loop) — a check that can never fail. This closes that hole structurally,
    before any code runs, so it is caught even in --fast mode.
    """
    for f in findings:
        ct = f.get("check_type")
        fid = f.get("id", "?")
        if ct in {"scalar", "proportion", "rate"}:
            if f.get("value") is None:
                fail("conditional:value", f"{fid}: {ct} requires a non-null 'value'")
        elif ct == "boolean":
            if not isinstance(f.get("value"), bool):
                fail("conditional:value", f"{fid}: boolean requires a bool 'value'")
        elif ct == "distribution":
            dist = f.get("distribution")
            if not isinstance(dist, dict) or not dist:
                fail("conditional:distribution", f"{fid}: distribution requires a non-empty 'distribution' object")
        elif ct == "matrix":
            mat = f.get("matrix")
            if not isinstance(mat, list) or not mat:
                fail("conditional:matrix", f"{fid}: matrix requires a non-empty 'matrix' list")
        elif ct == "quote_provenance":
            if not f.get("quote") or not f.get("source_locator"):
                fail("conditional:quote", f"{fid}: quote_provenance requires 'quote' and 'source_locator'")
    if not any(n.startswith("conditional") for n, _ in failures):
        ok("conditional:fields")


def check_counterfactual_tags(findings: list[dict]) -> None:
    for f in findings:
        tag = f.get("counterfactual_tag")
        if tag not in VALID_TAGS:
            fail("counterfactual:valid", f"{f.get('id')}: unknown tag {tag!r}")
        if tag == "OBSERVED" and not f.get("measurement_ref"):
            fail("counterfactual:observed_needs_ref",
                 f"{f.get('id')}: OBSERVED requires measurement_ref")
    # tag distribution sanity
    if findings:
        n_observed = sum(1 for f in findings if f.get("counterfactual_tag") == "OBSERVED")
        if n_observed / len(findings) > 0.6 and len(findings) > 5:
            warn("counterfactual:tag_distribution",
                 f"{n_observed}/{len(findings)} are OBSERVED — discipline may be decaying")
    if not any(n.startswith("counterfactual") for n, _ in failures):
        ok("counterfactual:tags")


def check_code_paths_resolve(findings: list[dict]) -> None:
    """Validate code_path: it must point at an existing file, with a suffix that
    is either a runnable function or a line reference — and REPLAYABLE_TYPES
    must use a runnable function (a line reference cannot verify their value).
    """
    for f in findings:
        fid = f.get("id")
        cp = f.get("code_path") or ""
        if ":" not in cp:
            fail("code_path:form",
                 f"{fid}: code_path {cp!r} must be 'file.py:function' or 'file.py:Lstart-Lend'")
            continue
        path_str, suffix = cp.rsplit(":", 1)
        if not path_str:
            fail("code_path:nonempty", f"{fid}: code_path has no file part")
            continue
        if not (ROOT / path_str).exists():
            fail("code_path:resolves", f"{fid}: {path_str} not found")
            continue
        kind = _suffix_kind(suffix)
        if kind == "invalid":
            fail("code_path:form",
                 f"{fid}: code_path suffix {suffix!r} is neither a function name nor Lstart-Lend")
        elif kind == "line_ref" and f.get("check_type") in REPLAYABLE_TYPES:
            fail("code_path:line_ref",
                 f"{fid}: check_type {f.get('check_type')!r} needs a runnable function in code_path, "
                 f"not a line reference ({suffix}) — its value cannot be replayed otherwise")
    if not any(n.startswith("code_path") for n, _ in failures):
        ok("code_path:resolves")


def check_revision_history(findings: list[dict]) -> None:
    for f in findings:
        hist = f.get("revision_history", [])
        if not isinstance(hist, list) or len(hist) == 0:
            fail("revision_history:nonempty", f"{f.get('id')}: revision_history must have ≥1 entry")
    if not any(n.startswith("revision_history") for n, _ in failures):
        ok("revision_history:nonempty")


def check_trust_memo_orphans(findings: list[dict]) -> None:
    if not TRUST_MEMO.exists():
        warn("trust_memo:exists", f"{TRUST_MEMO} not found — skipping orphan check")
        return
    txt = TRUST_MEMO.read_text()
    # Match the same id shape validate accepts, including the alpha suffix
    # (F-010b) — otherwise a cited F-010b is truncated to F-010 and false-flagged.
    cited = set(re.findall(r"F-\d{3,}[a-z]?", txt))
    known = {f.get("id") for f in findings if f.get("id")}
    orphans = cited - known
    if orphans:
        fail("trust_memo:orphans", f"TRUST_MEMO cites unknown findings: {sorted(orphans)}")
        return
    # abandonment check — guard against empty id sets (max() over empty raises)
    known_nums = [int(m.group(1)) for x in known if (m := re.match(r"^F-(\d+)", x))]
    cited_nums = [int(m.group(1)) for x in cited if (m := re.match(r"^F-(\d+)", x))]
    if known_nums and cited_nums:
        max_known, max_cited = max(known_nums), max(cited_nums)
        if max_known - max_cited > 10:
            warn("trust_memo:abandonment",
                 f"highest finding F-{max_known:03d} but TRUST_MEMO cites only up to F-{max_cited:03d}")
    ok("trust_memo:no_orphans")


def check_caveats_array(findings: list[dict]) -> None:
    for f in findings:
        cav = f.get("caveats")
        if not isinstance(cav, list):
            fail("caveats:list", f"{f.get('id')}: caveats must be a list")
        elif not cav:
            warn("caveats:empty", f"{f.get('id')} has empty caveats — OK if data is clean")
    if not any(n.startswith("caveats:list") for n, _ in failures):
        ok("caveats:list")


def check_data_contract_shape(findings: list[dict]) -> None:
    for f in findings:
        dc = f.get("data_contract")
        if not isinstance(dc, dict):
            fail("data_contract:dict", f"{f.get('id')}: data_contract must be an object")
            continue
        for k in ("source", "filters", "columns", "row_count_after_filter"):
            if k not in dc:
                fail("data_contract:fields", f"{f.get('id')}: data_contract missing {k!r}")
    if not any(n.startswith("data_contract") for n, _ in failures):
        ok("data_contract:shape")


def check_tolerances(findings: list[dict]) -> None:
    """A finding's replay tolerance is the trust knob for its numeric claim.
    Custom tolerances are allowed but capped (a tolerance wide enough to mask
    real drift is meaningless) and always surfaced as a warning so they are
    auditable rather than silent."""
    n_custom = 0
    for f in findings:
        t = f.get("tolerance")
        if t is None:
            continue
        fid = f.get("id", "?")
        if not isinstance(t, dict):
            fail("tolerance:shape", f"{fid}: tolerance must be an object with 'abs'/'rel'")
            continue
        n_custom += 1
        for name, cap in (("abs", _MAX_ABS_TOL), ("rel", _MAX_REL_TOL)):
            val = t.get(name)
            if val is None:
                continue
            if not isinstance(val, (int, float)) or val < 0:
                fail("tolerance:value", f"{fid}: tolerance.{name} must be a non-negative number")
            elif val > cap:
                fail("tolerance:loose",
                     f"{fid}: tolerance.{name}={val} exceeds the cap {cap} — too loose to be meaningful")
    if n_custom and not any(n.startswith("tolerance") for n, _ in failures):
        warn("tolerance:custom", f"{n_custom} finding(s) use a custom replay tolerance — audit them")
    if not any(n.startswith("tolerance") for n, _ in failures):
        ok("tolerance:bounds")


def check_source_hash_consistency(findings: list[dict]) -> None:
    """Per-claim replay has no shared pipeline DAG, so two findings could each
    replay green against *different* snapshots of the same source. Pinning a
    source hash and requiring all findings on a source to agree closes that gap."""
    by_source: dict[str, set] = {}
    n_unpinned = 0
    for f in findings:
        dc = f.get("data_contract") or {}
        src = dc.get("source")
        if not isinstance(src, str):
            continue
        h = dc.get("source_sha256")
        if h:
            by_source.setdefault(src, set()).add(h)
        else:
            n_unpinned += 1
    for src, hashes in by_source.items():
        if len(hashes) > 1:
            fail("source_hash:consistency",
                 f"findings disagree on the sha256 of {src} — different snapshots were used")
    if n_unpinned and not any(n.startswith("source_hash") for n, _ in failures):
        warn("source_hash:unpinned",
             f"{n_unpinned} finding(s) have no data_contract.source_sha256 — add it (register() stamps "
             "it automatically) so input drift is caught")
    if not any(n.startswith("source_hash") for n, _ in failures):
        ok("source_hash:consistency")


# Expected-schema lock file (opt-in). Produced by analysis.schemas.snapshot();
# maps a source path to a serialized Pandera schema. When present, validate
# re-checks each declared source against its locked schema to catch drift that
# conforms in row-count but not in shape/types/ranges.
SCHEMA_LOCK = ROOT / "analysis" / "output" / "schema-lock.json"


def check_schema_drift(findings: list[dict]) -> None:
    if not SCHEMA_LOCK.exists():
        return  # opt-in: no lock file → nothing to check
    try:
        registry = json.loads(SCHEMA_LOCK.read_text())
    except json.JSONDecodeError as e:
        fail("schema_drift:lock", f"schema-lock.json does not parse: {e}")
        return
    if not isinstance(registry, dict):
        fail("schema_drift:lock", "schema-lock.json must be a {source: schema} object")
        return
    try:
        import pandas as pd
        from pandera.pandas import DataFrameSchema
    except ImportError as e:
        fail("schema_drift:deps", f"schema-lock present but pandera/pandas unavailable: {e}")
        return
    for source, schema_json in registry.items():
        src = ROOT / source
        if not src.exists():
            warn("schema_drift:missing_source", f"{source} in schema-lock but file is absent")
            continue
        try:
            schema = DataFrameSchema.from_json(json.dumps(schema_json))
            df = pd.read_csv(src) if src.suffix == ".csv" else pd.read_excel(src)
            schema.validate(df, lazy=True)
        except Exception as e:
            fail("schema_drift", f"{source} no longer matches its locked schema: {type(e).__name__}: {e}")
    if not any(n.startswith("schema_drift") for n, _ in failures):
        ok("schema_drift:none")


# ─── replay (full mode) ─────────────────────────────────────────────────────

def _import_decisions() -> Any:
    """Import the project's _decisions.py if present. A syntax/import error in
    that file is a replay failure, not a crash that aborts every other check."""
    if not DECISIONS_MOD.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("_decisions", DECISIONS_MOD)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod
    except Exception as e:
        fail("replay:_decisions.py", f"could not import analysis/_decisions.py: {type(e).__name__}: {e}")
        return None


def _import_callable(code_path: str) -> tuple[Callable | None, str | None]:
    """code_path is 'analysis/02_profile.py:func_name'. Return (fn, error_msg).

    On success: (callable, None). On failure: (None, reason). The caller must
    treat None+reason as a replay failure, not a skip.
    """
    if ":" not in code_path:
        return None, f"code_path {code_path!r} has no ':func_name' suffix"
    file_str, fn_name = code_path.rsplit(":", 1)
    p = (ROOT / file_str).resolve()
    # Containment guard: never import code from outside the project root.
    if not p.is_relative_to(ROOT):
        return None, f"code_path escapes project root: {file_str}"
    if not p.exists():
        return None, f"file {file_str} does not exist"

    # Add project root to sys.path so 'from analysis._x import y' resolves
    # during the imported module's load.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    spec = importlib.util.spec_from_file_location(p.stem, p)
    if spec is None or spec.loader is None:
        return None, f"could not build import spec for {file_str}"
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return None, f"import of {file_str} raised: {type(e).__name__}: {e}"
    fn = getattr(mod, fn_name, None)
    if fn is None:
        return None, f"{fn_name} not found in {file_str}"
    if not callable(fn):
        return None, f"{fn_name} in {file_str} is not callable"
    return fn, None


def _apply_filters(df, filter_ids: list[str], decisions_mod) -> Any:
    """Apply DR-NNN filter functions in order. Each is `def DR_NNN(df) -> df`."""
    for dr in filter_ids:
        fn_name = dr.replace("-", "_")
        fn = getattr(decisions_mod, fn_name, None) if decisions_mod else None
        if fn is None:
            raise ValueError(f"filter {dr} not found in analysis/_decisions.py")
        df = fn(df)
    return df


# Analytical findings are routinely stored rounded for human consumption
# (e.g., 4.17 or 4.166667). 1e-6 abs tolerance lets findings stored to
# six decimal places replay green; relative tolerance handles large values.
# A finding MAY override these via a `tolerance: {abs, rel}` object, but the
# override is capped (see check_tolerances) and surfaced as a warning — the
# tolerance is the trust knob for numeric claims, so a loose one is auditable.
_TOL_ABS = 1e-6
_TOL_REL = 1e-9
_MAX_ABS_TOL = 1.0
_MAX_REL_TOL = 0.1


def _tols(f: dict) -> tuple[float, float]:
    t = f.get("tolerance") if isinstance(f.get("tolerance"), dict) else {}
    abs_t = t.get("abs", _TOL_ABS)
    rel_t = t.get("rel", _TOL_REL)
    # Clamp defensively so a malformed tolerance can't widen the gate past the cap.
    abs_t = abs_t if isinstance(abs_t, (int, float)) and 0 <= abs_t <= _MAX_ABS_TOL else _TOL_ABS
    rel_t = rel_t if isinstance(rel_t, (int, float)) and 0 <= rel_t <= _MAX_REL_TOL else _TOL_REL
    return abs_t, rel_t


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _replay_scalar(f: dict, value: Any) -> bool:
    expected = f.get("value")
    if expected is None:  # guard: a missing value must never replay green
        return False
    abs_t, rel_t = _tols(f)
    if isinstance(expected, (int, float)) and isinstance(value, (int, float)):
        return math.isclose(expected, value, rel_tol=rel_t, abs_tol=abs_t)
    return expected == value


def _replay_distribution(f: dict, dist: dict) -> bool:
    expected = f.get("distribution")
    if not isinstance(expected, dict) or not expected:  # empty → vacuous pass; reject
        return False
    if not isinstance(dist, dict):
        return False
    abs_t, rel_t = _tols(f)
    for k, v in expected.items():
        actual = dist.get(k)
        if actual is None:
            return False
        if not math.isclose(actual, v, rel_tol=rel_t, abs_tol=abs_t):
            return False
    return True


def _replay_quote(f: dict, _result: Any) -> bool:
    """Quote provenance: verify the quote text appears verbatim in source_locator."""
    quote = f.get("quote", "")
    locator = f.get("source_locator", "")
    if not quote or not locator:
        return False
    p = (ROOT / locator.split(":")[0]).resolve()
    # Containment guard: the source must live inside the project, otherwise the
    # claim is not reproducible from repo state.
    if not p.is_relative_to(ROOT) or not p.exists():
        return False
    return quote in p.read_text(errors="ignore")


def _replay_boolean(f: dict, value: Any) -> bool:
    expected = f.get("value")
    if not isinstance(expected, bool) or not isinstance(value, bool):
        return False
    return expected == value


def _replay_matrix(f: dict, mat: Any) -> bool:
    """Matrix: list-of-lists. Element-wise float compare with the same tolerance."""
    expected = f.get("matrix")
    if not expected or mat is None:
        return False
    if len(expected) != len(mat):
        return False
    abs_t, rel_t = _tols(f)
    for row_e, row_a in zip(expected, mat):
        if len(row_e) != len(row_a):
            return False
        for e, a in zip(row_e, row_a):
            if isinstance(e, (int, float)) and isinstance(a, (int, float)):
                if not math.isclose(e, a, rel_tol=rel_t, abs_tol=abs_t):
                    return False
            elif e != a:
                return False
    return True


REPLAY_DISPATCH = {
    "scalar": _replay_scalar,
    "proportion": _replay_scalar,
    "rate": _replay_scalar,
    "distribution": _replay_distribution,
    "quote_provenance": _replay_quote,
    "boolean": _replay_boolean,
    "matrix": _replay_matrix,
    # "manual" → handled in replay_finding directly (no callable invocation)
}


def replay_finding(f: dict, decisions_mod) -> tuple[bool, str]:
    """Return (ok, message)."""
    ct = f.get("check_type")

    if ct == "manual":
        # Documented-but-not-auto-replayable. Caller must surface as audit, not skip.
        return True, "manual check_type — no replay (audit by hand)"

    if ct == "quote_provenance":
        if _replay_quote(f, None):
            return True, "quote found in source"
        return False, f"quote not found at {f.get('source_locator')}"

    code_path = f.get("code_path") or ""
    # A replayable finding MUST name a runnable function. A line-ref or malformed
    # code_path is a hard failure here — never a silent "skip".
    if ":" not in code_path or _suffix_kind(code_path.rsplit(":", 1)[1]) != "callable":
        return False, (f"{ct} finding needs a runnable function in code_path to replay "
                       f"(got {code_path!r})")

    fn, err = _import_callable(code_path)
    if fn is None:
        return False, err or "could not import callable"

    try:
        # Most projects: function takes a dataframe pre-filtered by data_contract.
        # We pass the filtered df so the function focuses on computation.
        import pandas as pd
        dc = f["data_contract"]
        src = ROOT / dc["source"]
        if not src.exists():
            return False, f"source {src} missing"
        # Input identity: if the finding pinned the source hash, the file must
        # still match it. This is a stronger drift signal than row count — it
        # catches mutated cells, reordered rows, and schema changes that leave
        # the count unchanged.
        stored_hash = dc.get("source_sha256")
        if stored_hash and _file_sha256(src) != stored_hash:
            return False, f"source {dc['source']} changed since recorded (sha256 mismatch — data drift)"
        df = pd.read_csv(src) if src.suffix == ".csv" else pd.read_excel(src)
        df = _apply_filters(df, dc.get("filters", []), decisions_mod)
        if len(df) != dc["row_count_after_filter"]:
            return False, f"row count {len(df)} != contract {dc['row_count_after_filter']} (data drift?)"
        result = fn(df)
        replayer = REPLAY_DISPATCH.get(ct)
        if replayer is None:
            return False, f"no replayer for check_type {ct!r}"
        matched = replayer(f, result)
    except Exception as e:
        # Comparison runs inside the try so a wrong-typed result fails gracefully
        # instead of crashing the whole run with a traceback.
        return False, f"replay raised: {type(e).__name__}: {e}"

    if matched:
        return True, "value matches"
    return False, f"value mismatch: stored={f.get('value', f.get('distribution'))} computed={result}"


def run_replay(findings: list[dict]) -> None:
    decisions_mod = _import_decisions()
    if decisions_mod is None and any(f.get("data_contract", {}).get("filters") for f in findings):
        # Distinguish "missing" from "failed to import" (the latter already failed above)
        if not any(n == "replay:_decisions.py" for n, _ in failures):
            fail("replay:_decisions.py", "findings reference DR-NNN filters but analysis/_decisions.py is missing")
        return
    n_manual = 0
    for f in findings:
        fid = f.get("id", "?")
        ok_, msg = replay_finding(f, decisions_mod)
        if ok_:
            if f.get("check_type") == "manual":
                print(f"AUDIT  {fid}  manual  {msg}")
                n_manual += 1
            else:
                print(f"REPLAY {fid}  ok  {msg}")
        else:
            fail(f"replay:{fid}", msg)
    if n_manual:
        warn("replay:manual_findings",
             f"{n_manual} finding(s) have check_type=manual — auto-replay does not verify; audit by hand")


# ─── PROJECT-SPECIFIC checks ────────────────────────────────────────────────
# Add project-specific check functions below this line. Call them in main().
# Don't modify the dispatcher above — fix upstream in analysis-kit if needed.


def project_specific_checks(findings: list[dict]) -> None:
    """Override per project. Default: no-op."""
    pass


# ─── entrypoint ─────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="skip replay")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args()

    findings = load_findings()

    check_ids_unique(findings)
    check_required_fields(findings)
    check_check_types(findings)
    check_conditional_fields(findings)
    check_counterfactual_tags(findings)
    check_code_paths_resolve(findings)
    check_revision_history(findings)
    check_caveats_array(findings)
    check_data_contract_shape(findings)
    check_tolerances(findings)
    check_source_hash_consistency(findings)
    check_trust_memo_orphans(findings)

    project_specific_checks(findings)

    if not args.fast:
        check_schema_drift(findings)
        run_replay(findings)

    print()
    if failures:
        print(f"{len(failures)} FAILURES, {len(warnings_)} warnings")
        return 1
    if args.strict and warnings_:
        print(f"0 failures, {len(warnings_)} warnings (strict mode → treating as failure)")
        return 1
    print(f"ALL CHECKS PASSED ({len(warnings_)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
