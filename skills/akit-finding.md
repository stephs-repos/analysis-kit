---
name: akit-finding
description: Register a single finding in an analysis-kit project. Takes a one-line hypothesis ("median rating is 4.2 after dropping zero-sentinels"), drafts the function, data_contract, caveats, and counterfactual tag, shows the proposed JSON, asks the user to register. Invoked as /akit-finding "<hypothesis>".
---

# /akit-finding

Register one finding from a one-line hypothesis. This is the workhorse skill — invoke it every time you have a concrete claim worth tracking.

## Pre-flight

1. Confirm the cwd is an analysis-kit project: `analysis-kit.json` must exist. If not, stop and tell the user to run `/akit-start` first.

2. Parse the hypothesis from the invocation:
   - Expected: `/akit-finding "median rating is 4.2 after dropping zero-sentinels"`
   - If the hypothesis is empty or vague (one or two words), ask for a complete sentence: "what's the claim? Should be a complete sentence with a value, e.g., 'median session rating is 4.2 (n=312)'."

3. Confirm raw data is present. List `reference/raw-data/`. If empty (only README.md), stop and tell the user to drop data files first.

4. Read the existing `analysis/output/findings.json` to learn:
   - What `F-NNN` ids already exist (to compute the next id)
   - What patterns have been used (so the new finding fits)

5. Read `live-docs/DECISIONS.md` to learn what DR-NNN filters exist. Read `analysis/_decisions.py` to confirm they're implemented.

6. Read `memory/data_quality_caveats.md` for known caveats that might apply.

## Drafting

7. From the hypothesis, identify:

   a. **Source data file.** Which file in `reference/raw-data/` does this involve? If ambiguous, ask the user.

   b. **Columns.** Which columns does the claim depend on?

   c. **`check_type`.** Pick the most specific:
      - `scalar` — single number (count, mean, median, ratio)
      - `proportion` — a 0.0–1.0 ratio specifically
      - `rate` — a per-unit rate
      - `boolean` — yes/no assertion
      - `distribution` — summary stats (mean+std+quantiles)
      - `matrix` — 2D matrix (correlations, confusion)
      - `quote_provenance` — verbatim quote from source data
      - `manual` — heterogeneous, can't be auto-replayed (use sparingly)

   d. **Filters (`DR-NNN` ids).** Which existing DR-NNNs apply? If a needed filter doesn't exist yet:
      - Pause and tell the user: "this finding needs a filter that doesn't exist yet — for example, dropping rows where X = 0. Should I add `DR-NNN` to `_decisions.py` and document it in `DECISIONS.md`, or do you want to do that first?"
      - Don't silently skip the filter; that's exactly the kind of silent drift the framework catches.

   e. **Caveats.** Cross-reference `memory/data_quality_caveats.md`; pick caveat names that apply.

   f. **`counterfactual_tag`.** Default to `OBSERVED` for findings computed from data. Use `PLAUSIBLE` only if the claim is an inference with a named supporting pattern. Never `WEAK` for a finding worth registering.

   g. **`measurement_ref`.** Required when `counterfactual_tag` is `OBSERVED`. Should point to the function path (e.g., `analysis/02_profile.py:median_rating`) or a line range.

8. Compute the value(s) by writing or amending a function in the appropriate `analysis/NN_*.py` file. The function takes a *pre-filtered* DataFrame (validate.py applies filters before invoking) and returns the value in the shape the `check_type` expects.

   - For `scalar`: return a `float` or `int`
   - For `distribution`: return a `dict` with `mean`, `std`, `min`, `max`, `median`, `q25`, `q75`, `n`
   - For `boolean`: return a `bool`
   - For `matrix`: return a list of lists
   - Etc.

9. Compute the value by:
   - Loading the source file
   - Applying the listed filters in order
   - Verifying `len(df_filtered) == row_count_after_filter` (this is the value you'll record)
   - Calling the function on the filtered df
   - Capturing the result

10. Assemble the proposed finding as a JSON object using the next available F-NNN id. Show it to the user with annotations:

    ```json
    {
      "id": "F-005",
      "claim": "median session rating is 4.2 (n=312)",
      "check_type": "scalar",
      "code_path": "analysis/02_profile.py:median_session_rating",
      "value": 4.2,
      "n": 312,
      "data_contract": {
        "source": "reference/raw-data/sessions.csv",
        "filters": ["DR-001"],
        "columns": ["session_rating"],
        "row_count_after_filter": 312
      },
      "caveats": ["zero_sentinel_masked"],
      "counterfactual_tag": "OBSERVED",
      "measurement_ref": "analysis/02_profile.py:median_session_rating"
    }
    ```

    Plus any new code that would be added (the function, any new DR-NNN entries).

## Confirmation

11. Ask: "Register this as F-NNN? (y/edit/skip)"

    - On `y`: write the function to the analysis script (if new), call `_findings.register(...)` from a one-shot Python invocation, then run `python analysis/validate.py` (full mode) to confirm the new finding replays green.

    - On `edit`: ask what to change (claim text, filters, caveats, etc.), apply the edit to the proposed JSON, ask for confirmation again.

    - On `skip`: don't register; tell the user the proposal is discarded.

12. If validate.py passes after registration, confirm to the user:

    ```
    ✓ F-NNN registered. validate.py passed.
      Cite this in memos as `[F-NNN]`.
    ```

13. If validate.py fails, restore the previous state (don't leave the project in a broken state) and surface the error.

## Critical rules

- **Don't register without computing the value first.** A finding with `value=null` is meaningless and validate.py will fail anyway.
- **Don't skip the `data_contract.row_count_after_filter` field.** It's the highest-value field for catching silent drift; never leave it as 0 or null.
- **Don't auto-create new DR-NNN filters silently.** If the hypothesis needs a filter that doesn't exist, surface that as a separate decision and ask the user.
- **Never edit a finding by hand-editing `findings.json`.** Always go through `_findings.register()` or `_findings.update()` so revision_history stays correct.
- **Don't tag `OBSERVED` without a `measurement_ref`.** validate.py will reject it; the schema requires it. If the measurement isn't defensible, downgrade to `PLAUSIBLE` with a named supporting pattern, or `WEAK` (and don't publish it).
