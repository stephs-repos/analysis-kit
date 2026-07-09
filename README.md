# analysis-kit

A scaffolding framework for agentic data-analysis projects with [Claude Code](https://code.claude.com) as the operator.

The framework's job is **claim integrity**: every quantitative assertion you make to a stakeholder is backed by a finding ID, a reproducing code path, declared filters, and a counterfactual tag. Validation runs as exit-code; hooks block bad commits; templates carry caveats forward.

This is **scaffolding**, not a runtime library. Once a project is created, it has no runtime dependency on analysis-kit — upgrades are deliberate, opt-in copies of the templates.

## New user? The path is three steps

Onboarding is deliberately split at the scaffold boundary: this repo gets you **to** a project; everything after that lives **inside** the project you create.

```bash
# 1. Install: clone the kit and its skills (once per machine)
git clone <this-repo-url> ~/dev/analysis-kit
~/dev/analysis-kit/bootstrap/install-skills.sh   # /akit-* skills for Claude Code

# 2. Scaffold a project
~/dev/analysis-kit/bootstrap/new-project.sh ./my-analysis --minimum
#    (or, in Claude Code: /akit-start my-analysis)

# 3. Onboard inside the project
cd my-analysis && claude
```

From step 3 the interface is deliberately small: **add your files** (raw data → `reference/raw-data/`, project context → `reference/`), then **type `/akit-next`** — it detects where the project is, offers the single next step, and stops at every decision that's yours. Keep typing it until you're done. Every scaffold ships a `QUICKSTART.md` saying exactly this, with a two-minute preview of the phases it will walk you through.

Details and troubleshooting for step 1–2: [`bootstrap/INSTALL.md`](bootstrap/INSTALL.md).

### The skills

| Skill | Role |
|---|---|
| `/akit` | Index — explains the workflow and the skills. |
| `/akit-start <name>` | Scaffold a new project. |
| `/akit-fill` | Walk the `MUST_CUSTOMIZE` markers (accept/edit/skip each). |
| `/akit-finding "<hypothesis>"` | Register one finding — the workhorse, used continuously. |
| `/akit-next` | **Resumable conductor** — detects where the project is and routes you to the single next action. Run it anytime you're unsure what's next. |

See [`skills/`](skills/) for the source markdown.

## Documentation

To understand the system (read in this order):

- 🗺️ **[CONCEPTS.md](docs/CONCEPTS.md)** — the mental-model map: the main features in plain language and how they relate, with diagrams.
- 📖 **[USER_GUIDE.md](docs/USER_GUIDE.md)** — the detailed hands-on tour: how validation works, every template explained, common workflows, troubleshooting, when not to use.
- [PHILOSOPHY.md](docs/PHILOSOPHY.md) — principles

Reference (look up as needed):

- [PROVENANCE_CONTRACT.md](docs/PROVENANCE_CONTRACT.md) — `findings.json` schema reference
- [COUNTERFACTUAL_TAGGING.md](docs/COUNTERFACTUAL_TAGGING.md) — `OBSERVED` / `PLAUSIBLE` / `WEAK` rules
- [HOOKS_GUIDE.md](docs/HOOKS_GUIDE.md) — hook contracts and failure modes
- [REBUILD_PIPELINE.md](docs/REBUILD_PIPELINE.md) — Makefile targets and the CI trust gate

### VS Code dev container (recommended for working on analysis-kit itself)

The repo ships a `.devcontainer/` config so you can open it in VS Code with a reproducible environment in one click:

1. Open the repo folder in VS Code.
2. When prompted ("Reopen in Container"), accept — or run `Dev Containers: Reopen in Container` from the command palette.
3. Wait for the build (~2 min first time). Post-create runs `pytest` as a smoke test.

You get Python 3.13, pinned `pandas`/`pandera`/`numpy`/`pytest`, Quarto, `jq`, and the `gh` CLI — all verified together. See [`.devcontainer/`](.devcontainer/) for the exact pins.

Tiers:

- `--minimum` — CLAUDE.md, six live-docs, `validate.py`, `memory/`, `.claude/hooks/`. Pandera in deps.
- `--full` — adds the Quarto vignette pipeline and `_quarto.yml`.

## What you get

| Contract | File | Purpose |
|---|---|---|
| Trust gate | `analysis/validate.py` | Exit 0 = trustworthy. Stop hook fires `--fast`; commit hook blocks on full. |
| Claims ledger | `analysis/output/findings.json` | Every claim has `F-NNN` id, `code_path`, an `input` + `reproducibility` block, `caveats`, `counterfactual_tag`, `measurement_ref`. |
| Live docs | `live-docs/*.md` | TRUST_MEMO, DATA_PROFILE, DECISIONS, ANALYSIS_BACKLOG, TOOLING, METHODOLOGY_LOG — peers, all amendable. |
| Caveat carriers | `memory/*.md` | Preconditions the agent reads before aggregating. Templates declare shape, projects fill content. |
| Hooks | `.claude/hooks/` | validate-on-stop (fast, blocks the turn on red with a loop guard), block-unvalidated-commit (full, fails closed), findings-coverage-on-edit (nudge). |

## What this is *not*

- Not a pipeline runner. Use Kedro or Snakemake for orchestration.
- Not a notebook framework. Use Ploomber for notebook-first work.
- Not an MLflow replacement. Use MLflow for modelling.
- Not a BI tool. Use Evidence.dev for warehouse-resident BI.

It is dbt-tests-for-pandas-projects, with **claims** as the unit of trust, designed for an LLM operator.

## Philosophy

In one sentence: **constrain the agent's improvisational surface so deterministic guardrails can do the work.** See [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) for the full statement.

## Status

**v1.0.0.** The contracts are stable. A finding declares its data dependency in an `input` block (sources with pinned content hashes, columns) and a `reproducibility` block (filters, post-filter row count); values can be registered by execution (`register_computed`) so a number can't drift from the code that produced it. The self-test suite passes in CI across Python 3.11–3.13. Validated end-to-end against a 35-finding production project (caught 3 stale findings the project's own validator hadn't flagged). Quarto integration shipped; Datasette deferred to a later release.
