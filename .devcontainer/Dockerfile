# analysis-kit dev container — pinned for reproducibility.
#
# Base: Microsoft's devcontainers/python image, Python 3.13 on Debian Bookworm.
# Adds: jq (used by .claude/hooks), Quarto (used by --full tier vignettes).
#
# All Python dependencies are installed by post-create.sh so the workspace's
# pyproject.toml + requirements-dev.txt drives them, not the image.

FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

# System packages required at runtime
# - jq: parses Claude Code hook stdin in templates/.claude/hooks/*.sh
# - curl: pulls the Quarto installer (already present in base, but explicit)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        jq \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Quarto — pinned to a tested release. Used by templates/_quarto.yml and
# templates/vignettes/00_template.qmd in --full-tier scaffolds.
ARG QUARTO_VERSION=1.6.40
RUN curl -fsSL \
        "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.deb" \
        -o /tmp/quarto.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/quarto.deb \
    && rm /tmp/quarto.deb \
    && rm -rf /var/lib/apt/lists/*

USER vscode
