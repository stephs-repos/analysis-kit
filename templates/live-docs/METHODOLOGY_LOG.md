# Methodology Log — {{PROJECT_NAME}}

Narrative record of methodology moments — discoveries, decisions, AI mistakes caught, limitations surfaced. Failures count as much as wins.

## Format

Each entry:

- **Date** (absolute, e.g., `2026-05-14`)
- **Theme tag(s)** — see below
- **Narrative** (2–6 sentences)
- **Counterfactual** (optional, tagged `[OBSERVED]`, `[PLAUSIBLE]`, or `[WEAK]`)

### Theme tags

- `guardrails` — evaluation infrastructure, validation gates, deterministic checks
- `foundation` — exploratory analysis, ensuring solid base before inference
- `etl` — cleaning decisions, schema changes, masking
- `viz` — design choices, audience considerations, iteration
- `inference` — modelling, statistical work
- `human-in-loop` — places the human caught something the agent missed (or vice versa)

## Counterfactual discipline

Every "what would have happened without AI" claim must be defensible. Tag each `[OBSERVED]` (measurable), `[PLAUSIBLE]` (informed estimate, cite the pattern), or `[WEAK]` (rephrase or remove). When in doubt, soften.

See `docs/COUNTERFACTUAL_TAGGING.md` (in analysis-kit) for the full rules.

## Anchor metrics

Maintain a running tally at the bottom of this file. Defensible counts only.

## Entries

{{MUST_CUSTOMIZE — add your first entry once a methodology moment occurs.}}

---

## Anchor metrics tally

- Findings registered: 0
- DR-NNN decisions agreed: 0
- AI mistakes caught: 0
- Validate failures resolved: 0
- Last updated: {{CREATED_AT}}
