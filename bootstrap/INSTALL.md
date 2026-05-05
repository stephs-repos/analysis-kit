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

```bash
cd ~/dev/analysis-kit
pip install -e ".[dev]"
pytest tests/
```

All tests should pass. If they don't, file an issue rather than scaffolding from a broken kit.

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
