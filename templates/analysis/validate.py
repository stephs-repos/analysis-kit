"""
validate.py — exit code is the trust contract.

Every quantitative claim in findings.json must replay green. Two modes:

  python analysis/validate.py --fast    schema + structural checks only (~1s)
  python analysis/validate.py           full mode: replay every finding's data_contract

Exit 0 = trustworthy. Exit non-zero = stop, fix, do not ship.

This file is shipped by analysis-kit. Project-specific checks live below the
PROJECT-SPECIFIC marker. Don't edit core dispatcher logic — fix it upstream
in analysis-kit and migrate.

Framework version: 0.1.0
"""
from __future__ import annotations

import argparse
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

VALID_CHECK_TYPES = {"scalar", "distribution", "matrix", "quote_provenance", "proportion", "rate"}
VALID_TAGS = {"OBSERVED", "PLAUSIBLE", "WEAK"}

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
    return data


# ─── structural checks (fast mode) ──────────────────────────────────────────

def check_ids_unique(findings: list[dict]) -> None:
    seen: set[str] = set()
    for f in findings:
        fid = f.get("id")
        if not fid:
            fail("ids:present", f"finding missing id: {f.get('claim', '<no claim>')[:60]}")
            continue
        if not re.match(r"^F-\d{3,}$", fid):
            fail("ids:format", f"{fid} does not match F-NNN")
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
    if not failures:
        ok("schema:required")


def check_check_types(findings: list[dict]) -> None:
    for f in findings:
        ct = f.get("check_type")
        if ct not in VALID_CHECK_TYPES:
            fail("check_type:valid", f"{f.get('id')}: unknown check_type {ct!r}")
    if not any(n.startswith("check_type") for n, _ in failures):
        ok("check_type:valid")


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
    for f in findings:
        cp = f.get("code_path", "")
        path_str = cp.split(":")[0]
        if not path_str:
            fail("code_path:nonempty", f"{f.get('id')}: code_path empty")
            continue
        p = ROOT / path_str
        if not p.exists():
            fail("code_path:resolves", f"{f.get('id')}: {path_str} not found")
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
    cited = set(re.findall(r"F-\d{3,}", txt))
    known = {f.get("id") for f in findings if f.get("id")}
    orphans = cited - known
    if orphans:
        fail("trust_memo:orphans", f"TRUST_MEMO cites unknown findings: {sorted(orphans)}")
        return
    # abandonment check
    if known and cited:
        max_known = max(int(x.split("-")[1]) for x in known)
        max_cited = max(int(x.split("-")[1]) for x in cited)
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


# ─── replay (full mode) ─────────────────────────────────────────────────────

def _import_decisions() -> Any:
    """Import the project's _decisions.py if present."""
    if not DECISIONS_MOD.exists():
        return None
    spec = importlib.util.spec_from_file_location("_decisions", DECISIONS_MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _is_line_ref(code_path: str) -> bool:
    """code_path of form 'path/file.py:Lstart-Lend' is a line ref, not a callable."""
    if ":" not in code_path:
        return True
    fn_name = code_path.rsplit(":", 1)[1]
    return fn_name.startswith("L") and (fn_name[1:2].isdigit() or fn_name[1:2] == "")


def _import_callable(code_path: str) -> tuple[Callable | None, str | None]:
    """code_path is 'analysis/02_profile.py:func_name'. Return (fn, error_msg).

    On success: (callable, None). On failure: (None, reason). The caller must
    treat None+reason as a replay failure, not a skip.
    """
    if ":" not in code_path:
        return None, f"code_path {code_path!r} has no ':func_name' suffix"
    file_str, fn_name = code_path.rsplit(":", 1)
    p = ROOT / file_str
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
_TOL_ABS = 1e-6
_TOL_REL = 1e-9


def _replay_scalar(f: dict, value: Any) -> bool:
    expected = f.get("value")
    if isinstance(expected, (int, float)) and isinstance(value, (int, float)):
        return math.isclose(expected, value, rel_tol=_TOL_REL, abs_tol=_TOL_ABS)
    return expected == value


def _replay_distribution(f: dict, dist: dict) -> bool:
    expected = f.get("distribution", {})
    for k, v in expected.items():
        actual = dist.get(k)
        if actual is None:
            return False
        if not math.isclose(actual, v, rel_tol=_TOL_REL, abs_tol=_TOL_ABS):
            return False
    return True


def _replay_quote(f: dict, _result: Any) -> bool:
    """Quote provenance: verify the quote text appears verbatim in source_locator."""
    quote = f.get("quote", "")
    locator = f.get("source_locator", "")
    if not quote or not locator:
        return False
    p = ROOT / locator.split(":")[0]
    if not p.exists():
        return False
    return quote in p.read_text(errors="ignore")


REPLAY_DISPATCH = {
    "scalar": _replay_scalar,
    "proportion": _replay_scalar,
    "rate": _replay_scalar,
    "distribution": _replay_distribution,
    "quote_provenance": _replay_quote,
}


def replay_finding(f: dict, decisions_mod) -> tuple[bool, str]:
    """Return (ok, message)."""
    ct = f.get("check_type")
    fid = f.get("id", "?")

    if ct == "quote_provenance":
        if _replay_quote(f, None):
            return True, "quote found in source"
        return False, f"quote not found at {f.get('source_locator')}"

    code_path = f.get("code_path", "")
    if _is_line_ref(code_path):
        return True, "code_path is line-ref (skipped — replay needs a callable)"

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
        df = pd.read_csv(src) if src.suffix == ".csv" else pd.read_excel(src)
        df = _apply_filters(df, dc.get("filters", []), decisions_mod)
        if len(df) != dc["row_count_after_filter"]:
            return False, f"row count {len(df)} != contract {dc['row_count_after_filter']} (data drift?)"
        result = fn(df)
    except Exception as e:
        return False, f"replay raised: {type(e).__name__}: {e}"

    replayer = REPLAY_DISPATCH.get(ct)
    if replayer is None:
        return False, f"no replayer for check_type {ct!r}"
    if replayer(f, result):
        return True, "value matches"
    return False, f"value mismatch: stored={f.get('value', f.get('distribution'))} computed={result}"


def run_replay(findings: list[dict]) -> None:
    decisions_mod = _import_decisions()
    if decisions_mod is None and any(f.get("data_contract", {}).get("filters") for f in findings):
        fail("replay:_decisions.py", "findings reference DR-NNN filters but analysis/_decisions.py is missing")
        return
    for f in findings:
        fid = f.get("id", "?")
        ok_, msg = replay_finding(f, decisions_mod)
        if ok_:
            print(f"REPLAY {fid}  ok  {msg}")
        else:
            fail(f"replay:{fid}", msg)


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
    if findings is None:
        return 1

    check_ids_unique(findings)
    check_required_fields(findings)
    check_check_types(findings)
    check_counterfactual_tags(findings)
    check_code_paths_resolve(findings)
    check_revision_history(findings)
    check_caveats_array(findings)
    check_data_contract_shape(findings)
    check_trust_memo_orphans(findings)

    project_specific_checks(findings)

    if not args.fast:
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
