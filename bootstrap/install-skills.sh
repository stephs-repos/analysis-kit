#!/usr/bin/env bash
# install-skills.sh — install analysis-kit Claude Code skills into ~/.claude/skills/.
#
# Idempotent: re-running upgrades existing skills in place. Backs up overwritten
# files to ~/.claude/skills/.akit-backup-<timestamp>/ so accidental loss is
# recoverable.
#
# Each skill is templated at install time: the literal token __AKIT_ROOT__ is
# replaced with the absolute path to this analysis-kit clone, so the skills
# can find bootstrap/, templates/, etc. without environment variables.

set -euo pipefail

KIT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_SRC="$KIT_ROOT/skills"
TARGET="$HOME/.claude/skills"
BACKUP_DIR="$TARGET/.akit-backup-$(date -u +%Y%m%dT%H%M%SZ)"

if [ ! -d "$SKILLS_SRC" ]; then
  echo "error: skills/ not found at $SKILLS_SRC" >&2
  echo "are you running this from a clone of analysis-kit?" >&2
  exit 2
fi

mkdir -p "$TARGET"

SKILL_NAMES=(akit akit-start akit-fill akit-finding)
INSTALLED=0
BACKED_UP=0

for skill in "${SKILL_NAMES[@]}"; do
  src="$SKILLS_SRC/$skill.md"
  dst="$TARGET/$skill.md"

  if [ ! -f "$src" ]; then
    echo "warn: $src not found in this analysis-kit clone — skipping" >&2
    continue
  fi

  if [ -f "$dst" ]; then
    mkdir -p "$BACKUP_DIR"
    cp "$dst" "$BACKUP_DIR/$skill.md"
    BACKED_UP=$((BACKED_UP + 1))
  fi

  # Substitute __AKIT_ROOT__ with the absolute path to this clone.
  python3 -c "
import sys, pathlib
src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
kit_root = sys.argv[3]
dst.write_text(src.read_text().replace('__AKIT_ROOT__', kit_root))
" "$src" "$dst" "$KIT_ROOT"

  INSTALLED=$((INSTALLED + 1))
done

echo "✓ installed $INSTALLED skill(s) to $TARGET"
echo "  Skills: ${SKILL_NAMES[*]}"
if [ "$BACKED_UP" -gt 0 ]; then
  echo "  Backed up $BACKED_UP existing skill(s) to $BACKUP_DIR"
fi
echo
echo "Open Claude Code in any directory to invoke them — start with /akit for the index."
