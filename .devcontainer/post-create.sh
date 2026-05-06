#!/usr/bin/env bash
# post-create.sh — runs once after container creation.
#
# Installs analysis-kit + pinned dev dependencies, then runs the self-test
# suite as a smoke test. If pytest fails here, the container is misconfigured
# and the failure is visible immediately rather than later when someone
# tries to use it.

set -euo pipefail

cd "${CONTAINER_WORKSPACE_FOLDER:-/workspaces/analysis-kit}"

echo "→ installing pinned Python deps"
python -m pip install --upgrade pip
python -m pip install -r .devcontainer/requirements-dev.txt
python -m pip install -e .

echo
echo "→ tool versions"
python --version
pip --version
quarto --version
jq --version
gh --version | head -1
git --version

echo
echo "→ smoke test: running self-tests"
pytest tests/ -q

echo
echo "✓ analysis-kit dev container ready"
echo
echo "Try it out:"
echo "  ./bootstrap/new-project.sh /tmp/example --minimum"
echo "  cd /tmp/example && python analysis/validate.py --fast"
