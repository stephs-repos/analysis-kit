#!/usr/bin/env bash
# check-must-customize.sh — list MUST_CUSTOMIZE markers remaining in a project.
#
# Exit 0 if none remain, 1 if any remain. Use in CI to verify project is ready.
#
# A marker IS its placeholder syntax: the literal opening "{{MUST_CUSTOMIZE".
# We match that fixed string (grep -F), NOT the bare word, so that onboarding
# docs (README, CLAUDE.md) can refer to "MUST_CUSTOMIZE" in prose without
# false-positiving here. Invariant for template authors: never reproduce the
# literal "{{" + MUST_CUSTOMIZE token except as a real, to-be-filled marker —
# refer to markers by the bare word in prose.

set -e

TARGET="${1:-.}"
MARKER="{{MUST_CUSTOMIZE"

if [ ! -d "$TARGET" ]; then
  echo "not a directory: $TARGET" >&2
  exit 2
fi

count=$(grep -rFl "$MARKER" "$TARGET" \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=.venv \
  --exclude-dir=venv \
  2>/dev/null | wc -l)

if [ "$count" -eq 0 ]; then
  echo "✓ no MUST_CUSTOMIZE markers remain"
  exit 0
fi

echo "⚠ $count file(s) still contain MUST_CUSTOMIZE markers:"
grep -rFl "$MARKER" "$TARGET" \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=.venv \
  --exclude-dir=venv \
  2>/dev/null | sed "s|^|  |"

echo
echo "These files need project-specific content before the project is ready."
exit 1
