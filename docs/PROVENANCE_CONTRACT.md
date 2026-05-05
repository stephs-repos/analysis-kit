# Provenance contract

The `findings.json` schema is the API between the operator (Claude) and the trust gate (validate.py). This document defines the schema, versioning, and migration rules.

## Current schema version

`framework_version: 0.2.0`. Stored in each project's `analysis-kit.json`.

### Changelog

- **0.2.0** — Added `boolean` and `manual` check_types. `boolean` for assertions whose value is a Python bool (`function returns True/False, compared to stored`). `manual` for findings that are structurally documented but not auto-replayable; surface as `AUDIT` lines in validate output and emit a warning. Both surfaced when porting noise-solution's 35-finding set: 5 booleans (data-quality assertions, "X is true/false" findings) and 17 heterogeneous-dict findings that don't fit the typed enum cleanly. Promoted `matrix` from "shipped but untested" to "first-class with regression tests"; expects list-of-lists, element-wise float compare with the project tolerance.
- **0.1.0** — Initial schema: scalar, distribution, matrix, quote_provenance, proportion, rate.

## A finding

```json
{
  "id": "F-001",
  "claim": "median session rating is 4.2 (n=312)",
  "check_type": "scalar",
  "code_path": "analysis/02_profile.py:median_session_rating",
  "value": 4.2,
  "n": 312,
  "data_contract": {
    "source": "reference/raw-data/sessions.csv",
    "filters": ["DR-001", "DR-003"],
    "columns": ["session_rating"],
    "row_count_after_filter": 312
  },
  "caveats": ["zero_sentinel_masked", "ceiling_effect_present"],
  "counterfactual_tag": "OBSERVED",
  "measurement_ref": "analysis/02_profile.py:L120-L145",
  "revision_history": [
    {"timestamp": "2026-04-30T14:22:11Z", "reason": "initial entry"}
  ]
}
```

### Required fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | `F-NNN`. Monotonic per project. Never reused. |
| `claim` | string | Human-readable assertion, including `(n=N)`. |
| `check_type` | enum | `scalar`, `distribution`, `matrix`, `quote_provenance`, `proportion`, `rate`, `boolean`, `manual`. Validate.py dispatches on this. |
| `code_path` | string | `path/to/file.py:function_name` or `path/to/file.py:Lstart-Lend`. Must resolve. |
| `data_contract` | object | See below. |
| `caveats` | string[] | Cross-references to `memory/data_quality_caveats.md` entries. Empty array is allowed but `validate --strict` warns. |
| `counterfactual_tag` | enum | `OBSERVED`, `PLAUSIBLE`, `WEAK`. |
| `revision_history` | object[] | Append-only. Required even on initial entry. |

### Conditional fields

- `value`: required when `check_type` is `scalar`, `proportion`, `rate`, `boolean`.
- `n`: required when `check_type` is `scalar`, `proportion`, `rate`, `distribution`.
- `distribution`: required when `check_type == "distribution"`. Object with `min`, `q25`, `median`, `q75`, `max`, optionally `mean`, `std`.
- `matrix`: required when `check_type == "matrix"`. List of lists; element-wise float compare on numerics, exact compare on others.
- `quote`: required when `check_type == "quote_provenance"`. Verbatim text.
- `source_locator`: required when `check_type == "quote_provenance"`. Where in the source the quote was found.
- `measurement_ref`: required when `counterfactual_tag == "OBSERVED"`. Path:line reference to the measurement code.

### `manual` check_type

Use when a finding is structurally important but not naturally machine-replayable: heterogeneous nested dicts, qualitative judgements, snapshots whose comparison logic would be high-maintenance for low gain. Validate.py runs all structural checks (id, schema, data_contract, code_path resolves, etc.) and surfaces an `AUDIT` line plus a warning that this finding was not auto-verified. Promote to a typed check_type when a clear shape emerges across multiple manual findings.

### `data_contract` object

```json
{
  "source": "reference/raw-data/sessions.csv",
  "filters": ["DR-001", "DR-003"],
  "columns": ["session_rating"],
  "row_count_after_filter": 312
}
```

- `source`: relative path from project root. May be a list for multi-source findings.
- `filters`: array of `DR-NNN` ids from `live-docs/DECISIONS.md`. Validate.py uses these to reconstruct the row subset and recompute the value.
- `columns`: the columns the finding depends on. Schema-drift detection uses this.
- `row_count_after_filter`: integer. Lets validate detect silent row-count changes between data refreshes.

## Replay vs consistency

`validate.py` is a **replay harness**, not a consistency checker. For each finding:

1. Read `data_contract.source`.
2. Apply `data_contract.filters` (each `DR-NNN` is a Python function in `analysis/_decisions.py`).
3. Verify `len(df) == data_contract.row_count_after_filter`. Fail if not — schema or data drifted.
4. Run the function at `code_path`.
5. Compare the result to `value` / `distribution` / `matrix` / `quote`.
6. Pass if equal within tolerance, fail otherwise.

This is deliberately stricter than "rerun the script and see if numbers match" — it forces the operator to declare what data the claim is *about*, not just what the script happens to compute today.

## Schema migrations

Breaking changes to the schema bump `framework_version` major. Migration procedure:

1. New `framework_version` published in analysis-kit.
2. Migration script in `bootstrap/migrations/<from>_to_<to>.py` rewrites a project's `findings.json` to the new shape.
3. Downstream projects opt-in by running the migration script.

Non-breaking additions (new optional fields, new `check_type` values that validate.py treats as no-op when not understood) bump minor.

## Versioning rule

A project is "compliant with framework version N" if:

- `analysis-kit.json` declares version N.
- All findings have `check_type` valid in version N.
- `validate.py` is the version-N copy.

`bootstrap/check-compat.sh` (TODO v0.2) diffs the project's `validate.py` against the canonical version.
