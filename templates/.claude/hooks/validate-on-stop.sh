#!/usr/bin/env bash
# Stop hook — fast-mode validate. Runs after Claude finishes a turn.
#
# Non-zero exit reports validation failure to Claude in-turn but does NOT
# hard-block stop (community evidence: aggressive Stop-blocking causes
# false-positive premature-end behaviour). Hard block lives in the commit hook.
#
# Cost target: <2 seconds.

set -e

cd "${CLAUDE_PROJECT_DIR:-.}"

[ -f analysis/validate.py ] || exit 0

if ! python analysis/validate.py --fast 2>&1; then
  echo "validate.py --fast failed; see output above. Full replay runs at git commit time." >&2
  exit 1
fi

exit 0
