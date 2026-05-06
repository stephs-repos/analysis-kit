# Install

## Requirements

- Python 3.11+
- bash (POSIX-portable)
- `jq` (for hooks; install via `apt install jq` / `brew install jq`)
- git
- Optional: [Quarto](https://quarto.org) for vignette rendering (`--full` tier)
- Optional: `pipx install datasette` for `--full` exploration UI

## Install analysis-kit

```bash
git clone https://github.com/<your-user>/analysis-kit ~/dev/analysis-kit
```

## Verify

Two paths — pick one.

### Option A: VS Code dev container (recommended)

The repo ships `.devcontainer/`. Open the folder in VS Code, accept "Reopen in Container", wait for the build. Post-create installs the pinned dev environment and runs `pytest` automatically. If you see `35 passed` at the end, you're ready. Verified-working versions are checked in at `.devcontainer/requirements-dev.txt`.

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

## Upgrade an existing project

Migration scripts (when needed) live in `bootstrap/migrations/<from>_to_<to>.py`. v0.1 has none — first migration ships with v0.2.
