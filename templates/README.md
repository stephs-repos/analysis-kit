# {{PROJECT_NAME}}

{{MUST_CUSTOMIZE — one-paragraph project description, distilled from `memory/project_overview.md` (fill that file first).}}

Scaffolded from [analysis-kit]({{KIT_REPO_URL}}) v{{FRAMEWORK_VERSION}}.

> **New here?** Two things: add your files (raw data → `reference/raw-data/`, project context → `reference/`), then open Claude Code and type `/akit-next` — it guides you through everything else, one step at a time. [`QUICKSTART.md`](QUICKSTART.md) is the two-minute version of what to expect; [`CHEAT_SHEET.md`](CHEAT_SHEET.md) is the task → command lookup for later.

## First: fill in the template

This scaffold ships with six `MUST_CUSTOMIZE` markers — double-brace placeholders in the spots that need project-specific content. The single source is `memory/project_overview.md` (fill it first); this README's description and the `CLAUDE.md` goal paragraph are distilled from it, and the rest are the stakeholder stance, seed data caveats, and the data-profile inventory. **The project isn't set up until they're resolved**, so do this before running anything. (`FIRST_ENTRY` stubs elsewhere are different: they hold the spot for the first real decision, backlog item, or log entry, and fill themselves during analysis.)

```bash
# List files that still have unfilled markers (no analysis-kit clone needed).
# The \{\{ matches the literal double-brace that opens every marker:
grep -rlE '\{\{MUST_CUSTOMIZE' . --exclude-dir=.claude
```

Then fill them in:

- **With the analysis-kit skills installed:** drop your context into `reference/` (see [`reference/README.md`](reference/README.md)), then run `/akit-fill` — it drafts each marker from your reference materials and prompts you to accept/edit/skip.
- **Without the skills:** open this project in Claude Code and ask it to *"resolve the `MUST_CUSTOMIZE` markers, drafting each from `reference/` and the raw data."*

The structural setup is done when that `grep` returns nothing.

## Quick start

```bash
# Install deps
pip install -r requirements.txt

# Drop raw data into reference/raw-data/

# First inspection
python analysis/01_inspect_raw.py

# Profile + register first findings
python analysis/02_profile.py

# Verify (fast)
python analysis/validate.py --fast

# Verify (full replay)
python analysis/validate.py
```

## Discipline

This project follows the analysis-kit trust contract. See [`CLAUDE.md`](CLAUDE.md) for the full discipline. In short:

- Every quantitative claim has an `F-NNN` id, a code path, a data contract, and a counterfactual tag.
- `validate.py` exit code is the trust gate.
- Live documents (`live-docs/`) are amendable peers — keep them current.
- Caveats live in `memory/` so they reach the agent before aggregation.

## Contributing

Open Claude Code in this repo. It will read CLAUDE.md and follow the discipline. The Stop hook runs `validate.py --fast`; the commit hook blocks on full replay.
