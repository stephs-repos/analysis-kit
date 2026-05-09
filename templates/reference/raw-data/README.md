# reference/raw-data/

Drop your raw data files here.

The framework expects this directory to exist; scripts in `analysis/` and entries in `findings.json`'s `data_contract.source` field reference paths under `reference/raw-data/`.

## What goes here

- Original data files as you received them (CSV, Excel, Parquet, JSON, etc.)
- Treat these as **read-only**. Cleaning happens via `analysis/_decisions.py` (DR-NNN filters), not by editing the source files.
- If a vendor sends a v2 of a file, **keep both**. Renaming or overwriting is a silent-drift vector — see `docs/PROVENANCE_CONTRACT.md` (in analysis-kit) for why.

## What does NOT go here

- Cleaned/derived data — that lives in `analysis/output/` or is computed on demand
- Notes, dictionaries, briefs — those go directly in `reference/` (sibling of this directory), not inside `raw-data/`
- Anything you'd want version-controlled — by default this directory's contents are gitignored (override per-project as appropriate; see `.gitignore`)

## On gitignore

The default `.gitignore` ignores everything in this directory **except** this README, so the directory itself stays tracked. If you want to commit the raw data (small public datasets, fixtures), edit `.gitignore` to allow specific files:

```
# .gitignore additions for committable data
!reference/raw-data/sessions.csv
!reference/raw-data/demographics.csv
```

For private or large data, leave the gitignore as-is and distribute through your team's data store (S3, Drive, internal share).

## On data refreshes

When new versions of source files arrive, validate.py's `data_contract.row_count_after_filter` field is your early-warning system: if the post-filter row count changes after you swap in a new file, validate fails before you publish anything that depends on the old shape. See the user guide's "common workflows → 'I just got new raw data — what do I do?'" section.
