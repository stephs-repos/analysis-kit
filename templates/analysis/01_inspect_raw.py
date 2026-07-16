"""
01_inspect_raw.py — first-pass inspection of raw data.

Output: prints shape, dtypes, null counts, head to stdout.
Does NOT register findings yet — this is for the human/agent to read and
reason about, not for downstream validation.

Handles the layouts raw data actually arrives in: walks subdirectories,
reads CSV / Excel / JSON / zipped-CSV, and stays memory-safe on large files
(a bounded sample for dtypes/nulls plus a chunked pass for the true row
count — a multi-GB CSV must not OOM the first inspection).

Once you've decided what to formalize, write 02_profile.py and use
_findings.register() to enter claims.

{{FIRST_ENTRY}} — point RAW_DIR at your raw-data location, and extend the
format handling if your data arrives in something else (parquet, fixed-width…).
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "reference" / "raw-data"

# Sample size for dtypes/null-rates; the true row count is computed separately
# by streaming one column in chunks, so big files never load whole.
SAMPLE_ROWS = 200_000
SKIP_SUFFIXES = {".md", ".sha256", ".txt", ".gitkeep"}


def _describe(df: pd.DataFrame, *, sampled: bool = False, total_rows: int | None = None) -> None:
    label = f"shape (sampled {len(df):,} rows)" if sampled else "shape"
    print(f"{label}: {df.shape}")
    if total_rows is not None:
        print(f"true total rows: {total_rows:,}")
    print(f"dtypes:\n{df.dtypes}")
    tag = "null rate in sample" if sampled else "nulls per col"
    print(f"{tag}:\n{df.isna().sum()}")
    print(f"head:\n{df.head(3)}")


def _csv_sample_and_count(open_fn) -> tuple[pd.DataFrame, int]:
    """(sample df, true row count) without ever holding the whole file.
    open_fn returns a fresh file handle per call (a zip member can't be rewound)."""
    df = pd.read_csv(open_fn(), nrows=SAMPLE_ROWS,
                     encoding="utf-8-sig", encoding_errors="replace")
    total = sum(len(chunk) for chunk in pd.read_csv(
        open_fn(), usecols=[0], chunksize=500_000,
        encoding="utf-8-sig", encoding_errors="replace"))
    return df, total


def inspect_csv(p: Path) -> None:
    print(f"\n=== {p.relative_to(RAW_DIR)} ===")
    df, total = _csv_sample_and_count(lambda: open(p, "rb"))
    _describe(df, sampled=total > len(df), total_rows=total)


def inspect_zip(p: Path) -> None:
    with zipfile.ZipFile(p) as zf:
        for name in (n for n in zf.namelist() if n.lower().endswith(".csv")):
            print(f"\n=== {p.relative_to(RAW_DIR)} :: {name} ===")
            df, total = _csv_sample_and_count(lambda n=name: zf.open(n))
            _describe(df, sampled=total > len(df), total_rows=total)


def inspect_json(p: Path) -> None:
    print(f"\n=== {p.relative_to(RAW_DIR)} ===")
    obj = json.loads(p.read_text())
    records = obj if isinstance(obj, list) else None
    if records is None and isinstance(obj, dict):
        # APIs usually wrap the records (e.g. GBFS's data.stations) — take the
        # first list-of-dicts found at most one level down.
        candidates = list(obj.values())
        candidates += [v for d in obj.values() if isinstance(d, dict) for v in d.values()]
        records = next((v for v in candidates
                        if isinstance(v, list) and v and isinstance(v[0], dict)), None)
    if records is None:
        keys = list(obj)[:10] if isinstance(obj, dict) else type(obj).__name__
        print(f"  (unrecognized JSON shape; top level: {keys})")
        return
    _describe(pd.json_normalize(records))


def inspect_file(p: Path) -> None:
    if p.suffix in SKIP_SUFFIXES or p.name.startswith("."):
        return
    if p.suffix == ".csv":
        inspect_csv(p)
    elif p.suffix == ".zip":
        inspect_zip(p)
    elif p.suffix == ".json":
        inspect_json(p)
    elif p.suffix in (".xlsx", ".xls"):
        print(f"\n=== {p.relative_to(RAW_DIR)} ===")
        _describe(pd.read_excel(p))
    else:
        print(f"\n=== {p.relative_to(RAW_DIR)} ===\n  (skipping {p.suffix})")


def main() -> None:
    if not RAW_DIR.exists():
        print(f"raw data dir {RAW_DIR} not found")
        return
    for p in sorted(RAW_DIR.rglob("*")):
        if p.is_file():
            inspect_file(p)


if __name__ == "__main__":
    main()
