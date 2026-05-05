"""
schemas.py — Pandera schemas for raw and processed data.

Pandera handles the column/dtype/range layer of validation. validate.py
references schemas here to detect schema drift between data refreshes.

Usage in your scripts:

    from analysis.schemas import RawSessions
    df = RawSessions.validate(pd.read_csv("reference/raw-data/sessions.csv"))

{{MUST_CUSTOMIZE}} — replace the example below with your project's schemas.
"""
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


# ── Example schema — delete when you add your first real one ─────────────────
class RawSessions(pa.DataFrameModel):
    session_id: Series[str] = pa.Field(unique=True)
    session_rating: Series[float] = pa.Field(ge=0, le=5, nullable=True)

    class Config:
        strict = "filter"  # drop columns not declared, raise on missing
        coerce = True
