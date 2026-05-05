# Data Profile — {{PROJECT_NAME}}

Dictionary-aligned descriptive profile of every column in every file. **Self-contained for external distribution** — do not cross-reference internal working documents.

This document is generated/updated by `analysis/02_profile.py`. Re-run after raw data or dictionary changes.

## Files

{{MUST_CUSTOMIZE — list each file in `reference/raw-data/` with shape, source, snapshot date.}}

## Per-column profile

For each column:

- Type / inferred dtype
- Range / domain
- Null count and treatment
- Caveats (zero sentinel? scale mismatch? ceiling effect?)
- Cross-reference to `memory/data_quality_caveats.md` entry where applicable

## Last regenerated

{{CREATED_AT}}
