#!/usr/bin/env bash
# new-project.sh — scaffold a new analysis project from analysis-kit templates.
#
# Usage:
#   new-project.sh <target-dir> [--minimum|--full] [--name "Project Name"] [--github-user "username"]
#
# Defaults: --minimum tier, project name = basename of target dir, github-user = $USER.

set -euo pipefail

# ── arg parsing ─────────────────────────────────────────────────────────────

TARGET=""
TIER="minimum"
PROJECT_NAME=""
GITHUB_USER="${USER:-}"
AUTHOR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --minimum) TIER="minimum"; shift ;;
    --full) TIER="full"; shift ;;
    --name) PROJECT_NAME="$2"; shift 2 ;;
    --github-user) GITHUB_USER="$2"; shift 2 ;;
    --author) AUTHOR="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,9p' "$0"; exit 0 ;;
    *)
      if [ -z "$TARGET" ]; then TARGET="$1"; shift
      else echo "unexpected arg: $1" >&2; exit 2; fi
      ;;
  esac
done

if [ -z "$TARGET" ]; then
  echo "usage: $0 <target-dir> [--minimum|--full] [--name NAME] [--github-user USER]" >&2
  exit 2
fi

if [ -e "$TARGET" ] && [ "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "target $TARGET exists and is non-empty — refusing to overwrite" >&2
  exit 1
fi

[ -z "$PROJECT_NAME" ] && PROJECT_NAME="$(basename "$TARGET")"
[ -z "$AUTHOR" ] && AUTHOR="$(git config --global user.name 2>/dev/null || echo "$USER")"

KIT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATES="$KIT_ROOT/templates"
FRAMEWORK_VERSION="$(python3 -c "import json; print(json.load(open('$TEMPLATES/analysis-kit.json'))['framework_version'])" 2>/dev/null || echo "0.1.0")"
CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "→ scaffolding $PROJECT_NAME (tier: $TIER) into $TARGET"

# ── copy templates ─────────────────────────────────────────────────────────

mkdir -p "$TARGET"
cp -r "$TEMPLATES"/. "$TARGET/"

# Tier filtering — --minimum drops vignette + Quarto bits
if [ "$TIER" = "minimum" ]; then
  rm -rf "$TARGET/vignettes" "$TARGET/_quarto.yml"
fi

# ── token substitution ─────────────────────────────────────────────────────
# Replace ALL substitutable tokens. {{MUST_CUSTOMIZE}} stays — it marks intent.

# Single-pass Python walks the tree — simpler and more reliable than
# find+exec+exported-functions, which silently lost env vars in tests.
python3 - "$TARGET" <<PY
import pathlib

target = pathlib.Path("$TARGET")
subs = {
    "{{PROJECT_NAME}}": "$PROJECT_NAME",
    "{{GITHUB_USER}}": "$GITHUB_USER",
    "{{FRAMEWORK_VERSION}}": "$FRAMEWORK_VERSION",
    "{{CREATED_AT}}": "$CREATED_AT",
    "{{TIER}}": "$TIER",
    "{{AUTHOR}}": "$AUTHOR",
    "{{VIGNETTE_TITLE}}": "Untitled vignette",
}
exts = {".md", ".json", ".qmd", ".py", ".toml", ".yml", ".sh", ".txt"}

for p in target.rglob("*"):
    if not p.is_file() or p.suffix not in exts:
        continue
    try:
        txt = p.read_text()
    except UnicodeDecodeError:
        continue
    new = txt
    for k, v in subs.items():
        new = new.replace(k, v)
    if new != txt:
        p.write_text(new)
PY

# ── permissions ────────────────────────────────────────────────────────────

chmod +x "$TARGET/.claude/hooks/"*.sh

# ── git init ───────────────────────────────────────────────────────────────

if [ ! -d "$TARGET/.git" ]; then
  ( cd "$TARGET" && git init -q && git add -A && git commit -q -m "scaffold from analysis-kit v$FRAMEWORK_VERSION ($TIER tier)" )
fi

# ── done ───────────────────────────────────────────────────────────────────

echo
echo "✓ scaffolded $PROJECT_NAME at $TARGET (tier: $TIER, framework v$FRAMEWORK_VERSION)"
echo
echo "Next steps:"
echo "  cd $TARGET"
echo "  pip install -r requirements.txt"
echo "  # Drop raw data into reference/raw-data/"
echo "  # Open in Claude Code — it reads CLAUDE.md and follows the discipline."
echo
echo "Note: templates contain {{MUST_CUSTOMIZE}} markers. Run:"
echo "  $KIT_ROOT/bootstrap/check-must-customize.sh $TARGET"
echo "to see what still needs filling in."
