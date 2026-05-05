# CLAUDE.md — analysis-kit framework

This is the framework repo. **Not** a downstream project. Different rules apply here.

## What this repo is

A scaffolding kit for agentic data-analysis projects. `bootstrap/new-project.sh` copies `templates/` into a target dir and produces a self-contained project with no runtime dependency on this repo.

**Anchor metric:** every claim in a downstream project's `findings.json` must be reproducible by re-running `analysis/validate.py` and getting exit 0.

## Maintenance discipline

- **Templates are the product.** Never edit a downstream project's files when fixing a bug — fix the template here and document the migration.
- **Validate.py contract is the API.** Adding/renaming a `check_type` is a breaking change for every downstream project. Bump `framework_version` in `templates/analysis-kit.json`.
- **Self-tests must pass.** `pytest tests/` is the gate. Every PR runs validate.py against `tests/fixtures/synthetic/`.
- **Live docs in this repo:**
  - `docs/PHILOSOPHY.md` — principles (rarely changed)
  - `docs/PROVENANCE_CONTRACT.md` — findings.json schema (versioned)
  - `docs/COUNTERFACTUAL_TAGGING.md` — OBSERVED / PLAUSIBLE / WEAK rules
  - `docs/HOOKS_GUIDE.md` — hook contracts and failure modes

## When asked to add a feature

1. Is this scaffolding (template change) or runtime behaviour (validate.py / hooks change)?
2. Does it cross the tier line (`--minimum` vs `--full`)?
3. Does it add a dependency? Pandera, Quarto, Datasette are already in. Anything else needs justification.
4. Does it change `findings.json` schema? If yes, bump `framework_version` and write a migration note in `docs/PROVENANCE_CONTRACT.md`.

## When asked to debug a downstream project's validate failure

The fix usually lives in three places:
1. The downstream project's `analysis/output/findings.json` — wrong shape or missing `data_contract`.
2. The downstream project's project-specific check in their `validate.py`.
3. This repo's `templates/analysis/validate.py` core dispatcher — only if the failure pattern repeats across projects.

Default to fixing in the downstream project first. Only promote to the template if you've seen it twice.

## Conventions

- Python 3.11+. Pandera for column validation, pytest for self-tests.
- `bootstrap/new-project.sh` is bash, POSIX-portable. No Python at scaffold time (chicken-and-egg).
- Hooks in `templates/.claude/hooks/` are bash. `jq` is the only non-default dep — document it in `bootstrap/INSTALL.md`.
- Don't add an `npm`/`node` runtime to this repo. Quarto is a binary; Datasette is `pipx install`.

## Memory

This framework repo has its own auto-memory at `~/.claude/projects/-home-vscode-analysis-kit/memory/`. Downstream projects get their own memory dir scaffolded into `memory/` (in-repo, not auto-memory). Don't conflate the two.
