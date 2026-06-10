#!/usr/bin/env bash
# Stop hook — fast-mode validate when Claude finishes a turn.
#
# If validate.py --fast is red, this blocks the turn from ending (exit 2, with
# the failures on stderr so Claude sees them and fixes them). The stop_hook_active
# guard yields after one retry, so a persistently-red project can't trap Claude in
# an infinite stop → block → stop loop.
#
# Protocol (Claude Code hook spec):
#   exit 0          → allow the stop
#   exit 2 + stderr → block the stop; stderr is fed back to Claude
#
# Fails OPEN: if the loop guard can't be read (no jq) or the validator can't run,
# the stop is allowed — the safe failure for a Stop hook is "let it stop", never
# "loop forever".
#
# Cost target: <2 seconds (fast mode, no replay).

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
input=$(cat)

[ -f "$PROJECT_DIR/analysis/validate.py" ] || exit 0

# Loop guard: yield if we're already inside a stop-hook continuation. Without jq
# we can't read the guard, so we fail open rather than risk an infinite loop.
if command -v jq >/dev/null 2>&1; then
  [ "$(printf '%s' "$input" | jq -r '.stop_hook_active // false')" = "true" ] && exit 0
else
  exit 0
fi

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
command -v "$PY" >/dev/null 2>&1 || exit 0  # can't run → don't trap the turn

if ! out=$(cd "$PROJECT_DIR" && "$PY" analysis/validate.py --fast 2>&1); then
  {
    echo "validate.py --fast is red — resolve these before ending the turn:"
    echo "$out" | tail -n 40
  } >&2
  exit 2
fi

exit 0
