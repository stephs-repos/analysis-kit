---
name: Data quality caveats
description: Preconditions to apply before aggregation. Read this before computing any mean, median, count, or rate.
type: project
---

{{MUST_CUSTOMIZE — seed with caveats known BEFORE first data contact (stated collection quirks, suppression rules, known sentinels); skip if none are known yet. Profiling extends this file as more surface. Each entry should follow this shape:}}

### Caveat name (e.g., zero-sentinel in `column_X`)

- **Rule:** what to do (e.g., "mask 0 to NaN before aggregation")
- **Why:** why it matters (e.g., "0 is a 'not collected' sentinel, not 'absent'; aggregations otherwise silently understate")
- **How to apply:** mechanism (e.g., "use `DR-001` from `analysis/_decisions.py`; declare in `reproducibility.filters`")
- **Severity:** mandatory | recommended | informational
- **Discovery:** when/how the caveat was found (commit, finding id, conversation)

---

This file is a contract between the data and the operator. If you find yourself computing an aggregate over a column not represented here, **stop and ask** — there may be an undocumented caveat.
