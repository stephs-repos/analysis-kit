"""
01_inspect_raw.py — first-pass inspection of raw data.

Output: prints shape, dtypes, null counts, head/tail to stdout.
Does NOT register findings yet — this is for the human/agent to read and
reason about, not for downstream validation.

Once you've decided what to formalize, write 02_profile.py and use
_findings.register() to enter claims.

{{MUST_CUSTOMIZE}} — point RAW_DIR at your raw-data location.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "reference" / "raw-data"


def inspect_file(p: Path) -> None:
    print(f"\n=== {p.name} ===")
    if p.suffix == ".csv":
        df = pd.read_csv(p)
    elif p.suffix in (".xlsx", ".xls"):
        df = pd.read_excel(p)
    else:
        print(f"  (skipping {p.suffix})")
        return
    print(f"shape: {df.shape}")
    print(f"dtypes:\n{df.dtypes}")
    print(f"nulls per col:\n{df.isna().sum()}")
    print(f"head:\n{df.head(3)}")


def main() -> None:
    if not RAW_DIR.exists():
        print(f"raw data dir {RAW_DIR} not found")
        return
    for p in sorted(RAW_DIR.iterdir()):
        if p.is_file():
            inspect_file(p)


if __name__ == "__main__":
    main()
