# Decisions — {{PROJECT_NAME}}

Durable cleanup decisions (`DR-NNN`). Each entry corresponds to a function in `analysis/_decisions.py`.

Don't rename or delete entries — mark `superseded` or `dropped` instead so the trail is preserved.

## DR-NNN format

- **Status:** active | superseded | dropped
- **Rule:** what is applied
- **Why:** the reason this decision was made
- **Implementation:** function name in `analysis/_decisions.py`
- **Mandatory:** true if every aggregate over affected columns must apply this filter

## Decisions

{{FIRST_ENTRY — replace this stub with your project's first DR-NNN.}}

### DR-001 (example — replace or delete)

- **Status:** active
- **Rule:** Mask zero-sentinel values in `column_X` to NaN before aggregation.
- **Why:** `column_X` uses 0 to mean "not collected", not "absent". Means/medians silently understated when zeros are included.
- **Implementation:** `analysis/_decisions.py:DR_001`
- **Mandatory:** true
