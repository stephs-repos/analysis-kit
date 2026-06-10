#!/usr/bin/env bash
# PreToolUse hook on Bash — block a `git commit` of THIS project when validate.py
# is red.
#
# Protocol (Claude Code hook spec):
#   exit 0          → allow the tool call
#   exit 2 + stderr → block; stderr is fed back to Claude as the reason
#
# Fails CLOSED: if the gate cannot run (jq or python missing) a commit is
# blocked with an explanation, rather than letting an unverified commit through.
# A missing dependency never blocks non-commit commands.
#
# Commit detection is pattern-based and therefore approximate — it tolerates
# `git -C <dir> commit`, `git -c k=v commit`, and extra whitespace, but a
# determined bypass is possible. See docs/HOOKS_GUIDE.md "Bypass surface".
#
# Cost: full replay, up to ~30s on real projects. Fires only at commit time.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
input=$(cat)

# Match `git ... commit` at a command boundary (start, or after ; & | ( ).
# Tolerates -C/-c style flags with optional values and collapsed whitespace.
is_git_commit() {
  printf '%s' "$1" | grep -Eq \
    '(^|[;&|(])[[:space:]]*git([[:space:]]+-[A-Za-z-]+([[:space:]]+[^[:space:]]+)?)*[[:space:]]+commit([[:space:]]|$)'
}

if command -v jq >/dev/null 2>&1; then
  cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
  is_git_commit "$cmd" || exit 0
else
  # No jq: can't parse the payload precisely. Fall back to a coarse check on the
  # raw JSON — if it even looks like a commit, fail closed; otherwise allow.
  case "$input" in
    *git*commit*)
      echo "analysis-kit: jq is required to run the commit gate but isn't installed. Install jq (see bootstrap/INSTALL.md) or remove the hook from .claude/settings.json." >&2
      exit 2 ;;
    *) exit 0 ;;
  esac
fi

# It's a commit — run the gate, or fail closed.
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "analysis-kit: python3 is required to run validate.py but isn't installed." >&2
  exit 2
fi

# Not an analysis-kit project (no validator) → nothing to gate.
[ -f "$PROJECT_DIR/analysis/validate.py" ] || exit 0

if ! out=$(cd "$PROJECT_DIR" && "$PY" analysis/validate.py 2>&1); then
  {
    echo "BLOCKED: validate.py is red — fix the failing checks before committing."
    echo "$out" | tail -n 40
  } >&2
  exit 2
fi

exit 0
