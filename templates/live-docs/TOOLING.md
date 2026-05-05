# Tooling — {{PROJECT_NAME}}

Tool, library, and framework choices (`T-NNN`). Each entry records the choice, rationale, and status.

Don't rename or delete entries — mark `superseded` or `dropped` so the trail is preserved.

## T-NNN format

- **Status:** active | proposed | dropped | superseded
- **Choice:** what is adopted
- **Why:** rationale for this over alternatives
- **Alternatives considered:** what was looked at
- **Date:** when adopted/changed

## Adopted by default (from analysis-kit)

### T-001 — Pandera for column validation
- **Status:** active
- **Why:** lightweight, type-hint native, statistical hypothesis support; lighter than Great Expectations
- **Date:** at scaffold time

### T-002 — pandas/numpy for data manipulation
- **Status:** active
- **Why:** mainstream, broad ecosystem, agent-familiar
- **Date:** at scaffold time

## Project-specific

{{MUST_CUSTOMIZE — add T-NNN entries as your project picks visualisation libs, modelling tools, etc.}}
