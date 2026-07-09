"""
schemas.py — Pandera schemas for raw and processed data.

Pandera handles the column/dtype/range layer of validation: shape, types, and
ranges of the *input*, asserted before any aggregate is computed. This is a
separate concern from validate.py's replay (which checks that a stored *result*
re-derives). Call these schemas from your analysis scripts to fail fast on a
malformed refresh.

Usage in your scripts:

    from analysis.schemas import RawSessions
    df = RawSessions.validate(pd.read_csv("reference/raw-data/sessions.csv"))

{{FIRST_ENTRY}} — replace the example below with your project's schemas.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandera.pandas as pa
from pandera.typing import Series

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_LOCK = ROOT / "analysis" / "output" / "schema-lock.json"


# ── Example schema — delete when you add your first real one ─────────────────
class RawSessions(pa.DataFrameModel):
    session_id: Series[str] = pa.Field(unique=True)
    session_rating: Series[float] = pa.Field(ge=0, le=5, nullable=True)

    class Config:
        strict = "filter"  # drop columns not declared, raise on missing
        coerce = True


def snapshot(model: type[pa.DataFrameModel], source: str) -> Path:
    """Lock `model`'s expected schema for `source` into analysis/output/schema-lock.json.

    Once a source is locked, `validate.py` (full mode) re-checks the current
    data against the locked schema and fails on drift that conforms in row-count
    but not in shape/types/ranges — the kind row_count_after_filter can't catch.

    Run after the schema for a data refresh has settled, then commit the lock:

        from analysis.schemas import RawSessions, snapshot
        snapshot(RawSessions, "reference/raw-data/sessions.csv")
    """
    registry: dict = {}
    if SCHEMA_LOCK.exists():
        registry = json.loads(SCHEMA_LOCK.read_text())
    registry[source] = json.loads(model.to_schema().to_json())
    SCHEMA_LOCK.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_LOCK.write_text(json.dumps(registry, indent=2) + "\n")
    return SCHEMA_LOCK
