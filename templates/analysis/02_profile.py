"""
02_profile.py — descriptive profile + first findings.

This is where you formalize the inspection from 01 into checked claims.
Each function that produces a numeric or distributional result should:

1. Take a (filtered) DataFrame and return a value.
2. Be referenced by code_path in a findings.json entry.
3. Have its filters declared in the entry's reproducibility block.

{{MUST_CUSTOMIZE}} — replace the example below with your project's profile.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis._findings import register, register_computed, next_id  # noqa: F401

RAW = Path(__file__).resolve().parent.parent / "reference" / "raw-data"


# ── Example function referenced from findings.json ────────────────────────────
def median_session_rating(df: pd.DataFrame) -> float:
    """Median of session_rating after filters declared in reproducibility.

    Note: this function does NOT apply filters — validate.py applies the
    filters declared in reproducibility.filters before calling this.
    """
    return float(df["session_rating"].median())


def main() -> None:
    # Example: loading + filtering happens here in your normal flow.
    # validate.py replays this independently using input + reproducibility.
    src = RAW / "sessions.csv"
    if not src.exists():
        print(f"{src} missing — populate raw-data first")
        return
    df = pd.read_csv(src)
    # ... apply your DR-NNN filters here for the script's own use ...
    val = median_session_rating(df)
    print(f"median session rating: {val} (n={len(df)})")

    # Register as a finding (only if you don't already have one with this id):
    # Prefer register_computed — it runs the function and stores the RETURNED
    # value, so the number can't drift from the code that produced it.
    # register_computed(
    #     id=next_id(),
    #     claim=f"median session rating is {val:.2f} (n={len(df)})",
    #     check_type="scalar",
    #     code_path="analysis/02_profile.py:median_session_rating",
    #     input={
    #         "sources": [{"path": "reference/raw-data/sessions.csv"}],
    #         "columns": ["session_rating"],
    #     },
    #     reproducibility={
    #         "filters": [],  # add DR-NNN ids as agreed
    #     },
    #     caveats=[],
    #     counterfactual_tag="OBSERVED",
    #     measurement_ref="analysis/02_profile.py:median_session_rating",
    #     reason="initial profile",
    # )


if __name__ == "__main__":
    main()
