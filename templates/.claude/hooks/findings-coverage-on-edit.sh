#!/usr/bin/env bash
# PostToolUse hook on file edits — nudge Claude when an analysis compute script
# is edited, to re-validate and keep findings.json in sync.
#
# This is an advisory NUDGE, never a block. PostToolUse stdout on exit 0 goes
# only to the transcript (Claude doesn't see it), so the message is emitted as
# hookSpecificOutput.additionalContext, which IS added to Claude's context.
#
# Cost target: <200ms.

set -uo pipefail

input=$(cat)

# Advisory only — silently skip if jq isn't available.
command -v jq >/dev/null 2>&1 || exit 0

file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')
[ -n "$file_path" ] || exit 0

# Fire only for analysis compute scripts: numbered steps (analysis/NN_*.py) or
# the decisions module. The leading "/" and "*/analysis/" anchor at a path
# boundary so a directory like "reanalysis/" does not trigger.
case "/$file_path" in
  */analysis/[0-9][0-9]_*.py|*/analysis/_decisions.py)
    msg="You edited ${file_path}. If this changes how a finding's value is computed (or a DR-NNN filter), re-run \`python analysis/validate.py\` and update the affected findings via _findings.register_computed()/update() so findings.json stays in sync."
    jq -n --arg m "$msg" \
      '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $m}}'
    ;;
esac

exit 0
