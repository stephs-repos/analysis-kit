#!/usr/bin/env bash
# PostToolUse hook on Edit/Write — soft-warn if a file in analysis/ was changed
# without findings.json being touched in the last N commits.
#
# This is a NUDGE, not a block. Output goes to stdout (Claude sees it).
# Helps catch the "wrote analysis script, forgot to register a finding" case.
#
# Cost target: <500ms. Bounded git log; no replay.

set -e

cd "${CLAUDE_PROJECT_DIR:-.}"

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

# Only nudge for files in analysis/ that aren't infra
case "$file_path" in
  *analysis/[0-9][0-9]_*.py)
    # Did the most recent 3 commits touch findings.json?
    if git rev-parse --git-dir >/dev/null 2>&1; then
      recent_findings_changes=$(git log -3 --name-only --pretty=format: -- analysis/output/findings.json 2>/dev/null | grep -c findings.json || true)
      if [ "${recent_findings_changes:-0}" -eq 0 ]; then
        echo "(analysis-kit nudge: edited $file_path — consider whether a finding should be registered or updated in analysis/output/findings.json)"
      fi
    fi
    ;;
esac

exit 0
