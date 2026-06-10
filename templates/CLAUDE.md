# CLAUDE.md — {{PROJECT_NAME}}

**Project goal:** {{MUST_CUSTOMIZE — one paragraph: what this analysis is for, who reads it, what success looks like.}}

This project was scaffolded from [analysis-kit](https://github.com/{{GITHUB_USER}}/analysis-kit) v{{FRAMEWORK_VERSION}}. Framework version is pinned in `analysis-kit.json`; do not edit `analysis/validate.py` core dispatcher logic — fix upstream and migrate.

## Live documents — keep current

| File | Purpose | Update when… |
|---|---|---|
| [`live-docs/TRUST_MEMO.md`](live-docs/TRUST_MEMO.md) | What's reliable / noisy / unassessable; cites F-NNN ids | A new finding changes a recommendation, a limitation gets resolved |
| [`live-docs/DATA_PROFILE.md`](live-docs/DATA_PROFILE.md) | Dictionary-aligned descriptive profile of every column | Raw data or dictionary changes |
| [`live-docs/DECISIONS.md`](live-docs/DECISIONS.md) | Durable cleanup decisions (DR-NNN). Each DR-NNN must have a corresponding function in `analysis/_decisions.py`. | Any new cleanup rule is agreed |
| [`live-docs/ANALYSIS_BACKLOG.md`](live-docs/ANALYSIS_BACKLOG.md) | Analytical questions worth investigating (A-NNN) | A new analysis idea emerges |
| [`live-docs/TOOLING.md`](live-docs/TOOLING.md) | Tool/library/framework choices (T-NNN) | Any new tool is adopted, dropped, or superseded |
| [`live-docs/METHODOLOGY_LOG.md`](live-docs/METHODOLOGY_LOG.md) | Methodology narrative — discoveries, decisions, AI mistakes caught | After any meaningful methodology moment |

## The trust contract

Every quantitative claim in a memo, vignette, or stakeholder communication must:

1. Have an `F-NNN` id in `analysis/output/findings.json`.
2. Have a `code_path` that resolves, an `input` block declaring its source(s) and columns, and a `reproducibility` block declaring its filters and post-filter row count.
3. Pass `python analysis/validate.py` with exit 0.

Findings have `counterfactual_tag`: `OBSERVED` (measured, requires `measurement_ref`), `PLAUSIBLE` (informed estimate, supporting pattern named), or `WEAK` (rephrase or remove).

## Conventions

- Analysis scripts: `analysis/NN_*.py`. Numbered prefix indicates sequence.
- Output: `analysis/output/`. Findings: `analysis/output/findings.json`.
- Filters: `analysis/_decisions.py`. Function `DR_NNN(df) -> df` per `DECISIONS.md` entry.
- Schemas: `analysis/schemas.py`. Pandera-based.
- Vignettes: `vignettes/NN_*.qmd` (Quarto). Render with `quarto render vignettes/NN_topic.qmd`.

## Memory — caveat carriers

`memory/` contains preconditions to consult before aggregating. {{MUST_CUSTOMIZE — populate `memory/data_quality_caveats.md` with this project's specific zero-sentinels, scale mismatches, ceiling effects, masked rows.}}

When in doubt, read `memory/data_quality_caveats.md` before computing any aggregate.

## Don't

- Don't apply `--no-verify` to bypass hooks. If a hook is wrong, fix or remove it deliberately (visible in git).
- Don't compute aggregates without applying the relevant DR-NNN filters from `_decisions.py`.
- Don't add an `OBSERVED` claim without a `measurement_ref`.
- Don't rename or delete entries in `DECISIONS.md` or `ANALYSIS_BACKLOG.md` — mark `superseded` or `dropped`.
