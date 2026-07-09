# Install

## Requirements

- Python 3.11+
- bash (POSIX-portable)
- `jq` (for hooks; install via `apt install jq` / `brew install jq`). The commit gate fails *closed* without it — a missing `jq` blocks commits with an explanation rather than letting an unverified one through.
- git
- Optional: [Quarto](https://quarto.org) for vignette rendering (`--full` tier)
- Optional: `pipx install datasette` for `--full` exploration UI

## Install analysis-kit

```bash
git clone https://github.com/<your-user>/analysis-kit ~/dev/analysis-kit
```

## Install the Claude Code skills (recommended)

```bash
~/dev/analysis-kit/bootstrap/install-skills.sh
```

Installs the `/akit-*` workflow skills into `~/.claude/skills/` (idempotent; re-run after updating the kit). These give Claude Code the guided workflow — `/akit-start`, `/akit-fill`, `/akit-finding`, and the `/akit-next` conductor.

Note: scaffolded projects **embed** the in-project skills (`/akit`, `/akit-fill`, `/akit-finding`, `/akit-next`) in their own `.claude/skills/`, so collaborators cloning a project skip this step entirely. The global install mainly provides `/akit-start`, which you need before a project exists.

## Verify

Two paths — pick one.

### Option A: VS Code dev container (recommended)

The repo ships `.devcontainer/`. Open the folder in VS Code, accept "Reopen in Container", wait for the build. Post-create installs the pinned dev environment and runs `pytest` automatically. If you see all tests pass at the end (`N passed`, with no failures), you're ready. Verified-working versions are checked in at `.devcontainer/requirements-dev.txt`.

### Option B: local Python

```bash
cd ~/dev/analysis-kit
pip install -e ".[dev]"
pytest tests/
```

All tests should pass. If they don't, file an issue rather than scaffolding from a broken kit. If you hit a version mismatch, the `.devcontainer/requirements-dev.txt` set is the verified one — pin to those.

## Create a project

```bash
~/dev/analysis-kit/bootstrap/new-project.sh ~/work/my-analysis --minimum
```

Or with explicit options:

```bash
~/dev/analysis-kit/bootstrap/new-project.sh ~/work/my-analysis \
  --full \
  --name "Q2 customer churn analysis" \
  --github-user steph-swierenga \
  --author "Steph"
```

## Verify the new project

```bash
cd ~/work/my-analysis
~/dev/analysis-kit/bootstrap/check-must-customize.sh .
```

This lists remaining `{{MUST_CUSTOMIZE}}` markers — places the templates expect project-specific content.

## Onboard — continues inside the project

Installation ends here; onboarding doesn't. Every scaffolded project ships a `QUICKSTART.md` — the step-by-step recipe from empty scaffold to your first verified, committed finding. Open the project in Claude Code and follow it, or just type `/akit-next` and let it route you.

## Upgrade an existing project

Migration scripts (when needed) live in `bootstrap/migrations/<from>_to_<to>.py`. None are required through v1.0.0 — the pre-1.0 schema changes (including the v1.0 `data_contract` → `input`/`reproducibility` split) landed before the framework's first release, so there were no downstream projects to migrate.
