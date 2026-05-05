#!/usr/bin/env bash
# PreToolUse hook on Bash — blocks `git commit` when validate.py is red.
#
# Tool input arrives on stdin per Claude Code hook spec. Use jq to inspect.
# Exit 2 + stderr JSON = block. Exit 0 = allow.
#
# Full replay mode (the dangerous-moment gate). Cost: up to ~30s on real projects.
# This hook fires only at commit time, so the cost is amortised.
#
# MUST NOT call validate.py via the Stop hook machinery — independent invocation.

set -e

cd "${CLAUDE_PROJECT_DIR:-.}"

input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // ""')

case "$cmd" in
  *"git commit"*)
    [ -f analysis/validate.py ] || exit 0
    if ! python analysis/validate.py 2>&1; then
      cat <<EOF >&2
{"decision": "block", "reason": "validate.py is red — fix the failing checks before committing. Run \`python analysis/validate.py\` to see details."}
EOF
      exit 2
    fi
    ;;
esac

exit 0
