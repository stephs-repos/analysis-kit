---
name: Analysis framework
description: The trust contract in this project's context — provenance + replay discipline
type: feedback
---

This project follows the analysis-kit trust contract. Every quantitative claim must:

1. Have an `F-NNN` id in `analysis/output/findings.json`.
2. Have a `code_path` that resolves and a `data_contract` declaring filters, source, columns, and row count.
3. Pass `python analysis/validate.py` with exit 0.

**Why:** memos and vignettes lose credibility the moment a number can't be reproduced. Exit-code-as-truth is more durable than an LLM's self-assessment.

**How to apply:**

- Before adding any numeric assertion to a memo or vignette, ensure it has an F-NNN id and the entry passes validate.
- When stating a counterfactual (e.g., "without this filter, the result would be X"), tag it `[OBSERVED]` (with `measurement_ref`), `[PLAUSIBLE]` (with supporting pattern), or `[WEAK]` (rephrase or measure).
- When in doubt about a tag, soften.

See `CLAUDE.md` for project conventions and `docs/PHILOSOPHY.md` (in analysis-kit) for the full discipline.
