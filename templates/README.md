# {{PROJECT_NAME}}

{{MUST_CUSTOMIZE — one-paragraph project description.}}

Scaffolded from [analysis-kit](https://github.com/{{GITHUB_USER}}/analysis-kit) v{{FRAMEWORK_VERSION}}.

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
