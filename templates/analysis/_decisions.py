"""
_decisions.py — DR-NNN filter functions referenced from findings.json reproducibility.filters.

Each filter is a function that takes a DataFrame and returns a DataFrame.
The function name matches the DR-NNN id with hyphens replaced by underscores
(DR-001 → DR_001).

Filters should:
- Be pure: same input → same output, no side effects.
- Be idempotent: applying twice gives the same result as once.
- Document the rule in DECISIONS.md and reference back here.

{{MUST_CUSTOMIZE}} — this file ships as a stub. Add your project's filter
functions below as DR-NNN decisions are agreed in DECISIONS.md.
"""
from __future__ import annotations

import pandas as pd


# Example — delete this when you add your first real DR-NNN.
# def DR_001(df: pd.DataFrame) -> pd.DataFrame:
#     """Mask zero-sentinel in column X (DECISIONS.md DR-001)."""
#     return df.assign(X=df["X"].where(df["X"] != 0))
