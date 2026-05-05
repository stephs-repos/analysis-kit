#!/usr/bin/env bash
# check-must-customize.sh — list MUST_CUSTOMIZE markers remaining in a project.
#
# Exit 0 if none remain, 1 if any remain. Use in CI to verify project is ready.

set -e

TARGET="${1:-.}"

if [ ! -d "$TARGET" ]; then
  echo "not a directory: $TARGET" >&2
  exit 2
fi

count=$(grep -r "MUST_CUSTOMIZE" "$TARGET" \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=.venv \
  --exclude-dir=venv \
  -l 2>/dev/null | wc -l)

if [ "$count" -eq 0 ]; then
  echo "✓ no MUST_CUSTOMIZE markers remain"
  exit 0
fi

echo "⚠ $count file(s) still contain MUST_CUSTOMIZE markers:"
grep -r "MUST_CUSTOMIZE" "$TARGET" \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=.venv \
  --exclude-dir=venv \
  -l 2>/dev/null | sed "s|^|  |"

echo
echo "These files need project-specific content before the project is ready."
exit 1
