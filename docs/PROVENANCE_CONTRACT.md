# Provenance contract

The `findings.json` schema is the API between the operator (Claude) and the trust gate (validate.py). This document defines the schema, versioning, and migration rules.

## Current schema version

`framework_version: 1.0.0`. Stored in each project's `analysis-kit.json`.

### Changelog

- **1.0.0** — Contract restructure. The flat `data_contract` is split into two blocks that separate the two concerns it used to conflate: `input` (what the claim is *about* — `sources: [{path, sha256}]` and `columns`, asserted before compute) and `reproducibility` (how to re-derive it — `filters` and `row_count_after_filter`, asserted after). `sources` is a list, so a finding can declare every file it depends on (all are hash-pinned and schema-checked); a replayable finding must have exactly one source (multi-source findings are `manual`, since combining is project-specific). No migration: this lands before the framework's first release.
- **0.3.0** — Grounding & drift (additive). (1) **Input hashing**: a `source_sha256` pins the content hash of the input (introduced on `data_contract`; relocated to `input.sources[].sha256` in 1.0.0). `register()` stamps it automatically; replay fails if the source file changed since the finding was recorded (a stronger drift signal than row count — it catches mutated cells and reordered rows), and all findings on the same source must agree on the hash (so two claims can't silently use different snapshots). (2) **Execution-primary registration**: `register_computed()` runs `code_path` on the declared source and stores the *returned* value, so a number can't be supplied divorced from the code that produced it. (3) **Per-finding tolerance**: an optional `tolerance: {abs, rel}` overrides the replay default, capped (abs ≤ 1.0, rel ≤ 0.1) and surfaced as a warning so the trust knob stays auditable. (4) **Schema drift**: `analysis.schemas.snapshot()` locks a Pandera schema per source into `analysis/output/schema-lock.json`; when present, full-mode validate re-checks each source against its locked schema and fails on shape/type/range drift that conforms in row-count.
- **0.2.1** — Verifier hardening (no schema change; the validator only gets stricter, matching what this contract always documented). Closed two holes that let a finding pass without being verified: (1) a `code_path` with no function name, or a line reference (`:Lstart-Lend`) on a replayable check_type, now **fails** — a value that can't be re-run isn't a verified value, so replayable check_types must name a runnable function (line references remain valid for `manual` findings and for `measurement_ref`); (2) conditional payload fields (`value`, `distribution`, `matrix`, `quote`/`source_locator`) are now **enforced structurally**, so a payload-less finding can no longer replay vacuously. Also: malformed `findings.json` (non-object entries, null fields, NaN values) fails gracefully instead of crashing; `code_path`/quote sources are confined to the project root; `_findings.register()` rejects the same defects before they reach disk.
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
  "input": {
    "sources": [
      {"path": "reference/raw-data/sessions.csv", "sha256": "9f86d08..."}
    ],
    "columns": ["session_rating"]
  },
  "reproducibility": {
    "filters": ["DR-001", "DR-003"],
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
| `code_path` | string | `path/to/file.py:function_name` (a runnable function) or `path/to/file.py:Lstart-Lend` (a line reference). Must resolve. **Replayable check_types** (`scalar`, `proportion`, `rate`, `boolean`, `distribution`, `matrix`) require the `:function_name` form — their value is verified by re-running it. The `:Lstart-Lend` form is only valid for `manual` findings. |
| `input` | object | What the claim is about: `sources` (list of `{path, sha256}`) and `columns`. See below. |
| `reproducibility` | object | How to re-derive: `filters` and `row_count_after_filter`. See below. |
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
- `tolerance`: optional object `{abs, rel}` overriding the replay tolerance for numeric check_types. Capped at `abs ≤ 1.0`, `rel ≤ 0.1`; any custom tolerance is surfaced as a warning so it stays auditable.

### `manual` check_type

Use when a finding is structurally important but not naturally machine-replayable: heterogeneous nested dicts, qualitative judgements, snapshots whose comparison logic would be high-maintenance for low gain. Validate.py runs all structural checks (id, schema, input/reproducibility, code_path resolves, etc.) and surfaces an `AUDIT` line plus a warning that this finding was not auto-verified. Promote to a typed check_type when a clear shape emerges across multiple manual findings.

### `input` object

```json
{
  "sources": [
    {"path": "reference/raw-data/sessions.csv", "sha256": "9f86d08..."}
  ],
  "columns": ["session_rating"]
}
```

- `sources`: list of input files, each `{path, sha256}`. `path` is relative to the project root. `sha256` is the content hash, stamped by `register()` when the file is present; when set, replay fails if the file changed since the finding was recorded (a stronger drift signal than row count — it catches mutated cells and reordered rows), and all findings on the same path must agree on it. A **replayable** check_type must have exactly one source; multi-source findings (which a project must combine itself) are `manual`.
- `columns`: the columns the finding depends on. Documentary; the live drift signals are `reproducibility.row_count_after_filter`, the source hashes, and (when locked) the Pandera schema in `schema-lock.json`.

### `reproducibility` object

```json
{
  "filters": ["DR-001", "DR-003"],
  "row_count_after_filter": 312
}
```

- `filters`: array of `DR-NNN` ids from `live-docs/DECISIONS.md`. Validate.py uses these to reconstruct the row subset and recompute the value.
- `row_count_after_filter`: integer. Lets validate detect silent row-count changes between data refreshes. Required for replayable check_types; optional for `manual`.

## Replay vs consistency

`validate.py` is a **replay harness**, not a consistency checker. For each replayable finding:

1. Read the single `input.sources[0]`; if its `sha256` is pinned, verify the file still matches it.
2. Apply `reproducibility.filters` (each `DR-NNN` is a Python function in `analysis/_decisions.py`).
3. Verify `len(df) == reproducibility.row_count_after_filter`. Fail if not — schema or data drifted.
4. Run the function at `code_path`.
5. Compare the result to `value` / `distribution` / `matrix` / `quote`.
6. Pass if equal within tolerance, fail otherwise.

This is deliberately stricter than "rerun the script and see if numbers match" — it forces the operator to declare what data the claim is *about*, not just what the script happens to compute today.

### What replay does and does not prove

Replay proves **stability**: the stored number still re-derives from the declared data and code, so it has not silently drifted. It does **not** prove **correctness**. In particular, replay cannot detect a *correct computation of the wrong question* — if the operator pointed the finding at the wrong column, cohort, or filter, replay will happily confirm the wrong number re-derives. The `counterfactual_tag` (and human review of the `claim` against the `code_path`) is what guards that boundary; the validator guards drift.

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

A `bootstrap/check-compat.sh` that diffs the project's `validate.py` against the canonical version is on the roadmap (not yet implemented).
