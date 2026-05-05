# analysis-kit

A scaffolding framework for agentic data-analysis projects with [Claude Code](https://code.claude.com) as the operator.

The framework's job is **claim integrity**: every quantitative assertion you make to a stakeholder must be backed by a finding ID, a reproducing code path, declared filters, and a counterfactual tag. Validation runs as exit-code; hooks block bad commits; templates carry caveats forward.

This is **scaffolding**, not a runtime library. Once a project is created, it has no runtime dependency on analysis-kit — upgrades are deliberate, opt-in copies of the templates.

## Quick start

```bash
# Clone analysis-kit somewhere
git clone <your-fork-url> ~/dev/analysis-kit

# Create a new analysis project
~/dev/analysis-kit/bootstrap/new-project.sh ./my-analysis --minimum

cd my-analysis
claude            # opens Claude Code; reads CLAUDE.md → follows the discipline
```

Tiers:

- `--minimum` — CLAUDE.md, six live-docs, validate.py, memory/, .claude/hooks/. Pandera in deps.
- `--full` — adds Quarto vignette pipeline, `_quarto.yml`, optional Datasette UI, render scripts.

## What you get

| Contract | File | Purpose |
|---|---|---|
| Trust gate | `analysis/validate.py` | Exit 0 = trustworthy. Stop hook blocks turn-end if red on `--fast`; commit hook blocks on full. |
| Claims ledger | `analysis/output/findings.json` | Every claim has F-NNN id, `code_path`, `data_contract`, `caveats`, `counterfactual_tag`, `measurement_ref`. |
| Live docs | `live-docs/*.md` | TRUST_MEMO, DATA_PROFILE, DECISIONS, ANALYSIS_BACKLOG, TOOLING, METHODOLOGY_LOG — peers, all amendable. |
| Caveat carriers | `memory/*.md` | Preconditions Claude touches before aggregating. Templates declare shape, projects fill content. |
| Hooks | `.claude/hooks/` | validate-on-stop (fast), block-unvalidated-commit (full), findings-coverage-on-edit. |

## What this is *not*

- Not a pipeline runner. Use Kedro or Snakemake for orchestration if you need it.
- Not a notebook framework. Use Ploomber for notebook-first work.
- Not an MLflow replacement. Use MLflow for modelling.
- Not a BI tool. Use Evidence.dev for warehouse-resident BI.

It is dbt-tests-for-pandas-projects, with **claims** as the unit of trust, designed for an LLM operator.

## Philosophy

See [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) for the full statement. In one sentence: **constrain the agent's improvisational surface so deterministic guardrails can do the work**.

## Status

v0.1 — early. The five contracts are stable; tier system, Pandera integration, and self-tests work. Quarto integration is partial.
