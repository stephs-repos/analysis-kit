"""
_decisions.py — DR-NNN filter functions referenced from findings.json reproducibility.filters.

Each filter is a function that takes a DataFrame and returns a DataFrame.
The function name matches the DR-NNN id with hyphens replaced by underscores
(DR-001 → DR_001).

Filters should:
- Be pure: same input → same output, no side effects.
- Be idempotent: applying twice gives the same result as once.
- Document the rule in DECISIONS.md and reference back here.

{{FIRST_ENTRY}} — this file ships as a stub. Add your project's filter
functions below as DR-NNN decisions are agreed in DECISIONS.md.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


# Example — delete this when you add your first real DR-NNN.
# def DR_001(df: pd.DataFrame) -> pd.DataFrame:
#     """Mask zero-sentinel in column X (DECISIONS.md DR-001)."""
#     return df.assign(X=df["X"].where(df["X"] != 0))


def decisions_fingerprint() -> str:
    """Hash of the ENTIRE _decisions.py source.

    Any change to a rule's logic changes this — including module-level constants
    or helpers a rule depends on, which a per-function hash would miss. Used by
    the provenance manifest of a materialised intermediate table (see
    analysis/_provenance.py) so validate's freshness check can detect a derived
    table gone stale against the DRs, not just against the raw bytes.

    Deliberately coarse: altering any DR marks every derived table that pins this
    fingerprint as stale — a safe over-trigger (a false rebuild beats a silent
    false-green). Works even on the stub (no DRs yet): it just hashes this file.
    """
    return hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
