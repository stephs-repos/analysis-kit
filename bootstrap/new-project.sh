#!/usr/bin/env bash
# new-project.sh — scaffold a new analysis project from analysis-kit templates.
#
# Usage:
#   new-project.sh <target-dir> [--minimum|--full] [--name "Project Name"] [--github-user "username"] [--author "Name"]
#
# Defaults: --minimum tier, project name = basename of target dir, github-user = $USER.

set -euo pipefail

# ── arg parsing ─────────────────────────────────────────────────────────────

TARGET=""
TIER="minimum"
PROJECT_NAME=""
GITHUB_USER="${USER:-}"
AUTHOR=""

# require_value FLAG REMAINING-ARGC — fail clearly when a value-taking flag is last.
require_value() {
  if [ "$2" -lt 2 ]; then
    echo "missing value for $1" >&2
    exit 2
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --minimum) TIER="minimum"; shift ;;
    --full) TIER="full"; shift ;;
    --name) require_value "$1" "$#"; PROJECT_NAME="$2"; shift 2 ;;
    --github-user) require_value "$1" "$#"; GITHUB_USER="$2"; shift 2 ;;
    --author) require_value "$1" "$#"; AUTHOR="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,7p' "$0"; exit 0 ;;
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

if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "target $TARGET exists and is non-empty — refusing to overwrite" >&2
  exit 1
fi

[ -z "$PROJECT_NAME" ] && PROJECT_NAME="$(basename "$TARGET")"
[ -z "$AUTHOR" ] && AUTHOR="$(git config --global user.name 2>/dev/null || echo "${USER:-unknown}")"

KIT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATES="$KIT_ROOT/templates"

# Read framework_version without a Python dependency (pure grep/sed) so the
# version is correct even on a host where the substitution step would fail.
FRAMEWORK_VERSION="$(grep -o '"framework_version"[[:space:]]*:[[:space:]]*"[^"]*"' "$TEMPLATES/analysis-kit.json" 2>/dev/null | head -1 | sed 's/.*"\([^"]*\)"[[:space:]]*$/\1/')"
[ -z "$FRAMEWORK_VERSION" ] && FRAMEWORK_VERSION="unknown"
CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Clean up a half-scaffolded target if anything below fails — but only if WE
# created it (never delete a directory the user already had).
TARGET_PREEXISTED=0
[ -e "$TARGET" ] && TARGET_PREEXISTED=1
cleanup() {
  code=$?
  if [ "$code" -ne 0 ] && [ "$TARGET_PREEXISTED" -eq 0 ] && [ -e "$TARGET" ]; then
    rm -rf "$TARGET"
    echo "scaffold failed (exit $code) — removed partial $TARGET" >&2
  fi
}
trap cleanup EXIT

echo "→ scaffolding $PROJECT_NAME (tier: $TIER) into $TARGET"

# ── copy templates ─────────────────────────────────────────────────────────

mkdir -p "$TARGET"
cp -r "$TEMPLATES"/. "$TARGET/"

# Tier filtering — --minimum drops vignette + Quarto bits, and the render-only
# deps in requirements.txt (matplotlib/jupyter/pyyaml are useless without
# vignettes). The Makefile and CI workflow are kept for both tiers: their
# validate/findings targets and the trust gate apply regardless, and the render
# target self-skips when there's no _quarto.yml.
if [ "$TIER" = "minimum" ]; then
  rm -rf "$TARGET/vignettes" "$TARGET/_quarto.yml"
  # Strip the full-tier-only render dependency block (from its marker to EOF).
  sed -i '/^# --- vignette rendering/,$d' "$TARGET/requirements.txt"
fi

# ── token substitution ─────────────────────────────────────────────────────
# Replace ALL substitutable tokens. {{MUST_CUSTOMIZE}} stays — it marks intent.
#
# The heredoc is QUOTED (<<'PY') and values are passed via the environment, not
# interpolated into the source. This is the safety boundary: a project name or
# author containing quotes, backslashes, or shell metacharacters is data, never
# code. (Python here is stdlib-only — no third-party deps at scaffold time.)
AKIT_TARGET="$TARGET" \
AKIT_PROJECT_NAME="$PROJECT_NAME" \
AKIT_GITHUB_USER="$GITHUB_USER" \
AKIT_FRAMEWORK_VERSION="$FRAMEWORK_VERSION" \
AKIT_CREATED_AT="$CREATED_AT" \
AKIT_TIER="$TIER" \
AKIT_AUTHOR="$AUTHOR" \
python3 - <<'PY'
import os
import pathlib

target = pathlib.Path(os.environ["AKIT_TARGET"])
subs = {
    "{{PROJECT_NAME}}": os.environ["AKIT_PROJECT_NAME"],
    "{{GITHUB_USER}}": os.environ["AKIT_GITHUB_USER"],
    "{{FRAMEWORK_VERSION}}": os.environ["AKIT_FRAMEWORK_VERSION"],
    "{{CREATED_AT}}": os.environ["AKIT_CREATED_AT"],
    "{{TIER}}": os.environ["AKIT_TIER"],
    "{{AUTHOR}}": os.environ["AKIT_AUTHOR"],
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
  (
    cd "$TARGET" && git init -q && git add -A
    # Fall back to a scaffold identity so the initial commit works on machines
    # (CI, fresh containers) with no global git config. Use --author's name when
    # provided so the commit isn't attributed to a generic identity.
    if git config user.email >/dev/null 2>&1; then
      git commit -q -m "scaffold from analysis-kit v$FRAMEWORK_VERSION ($TIER tier)"
    else
      git -c user.name="${AUTHOR:-analysis-kit}" -c user.email="analysis-kit@localhost" \
        commit -q -m "scaffold from analysis-kit v$FRAMEWORK_VERSION ($TIER tier)"
    fi
  )
fi

# ── done ───────────────────────────────────────────────────────────────────

echo
echo "✓ scaffolded $PROJECT_NAME at $TARGET (tier: $TIER, framework v$FRAMEWORK_VERSION)"
echo
echo "Next steps:"
echo "  cd '$TARGET'"
echo "  pip install -r requirements.txt"
echo "  # Drop raw data into reference/raw-data/"
echo "  # Open in Claude Code — it reads CLAUDE.md and follows the discipline."
echo
echo "Note: templates contain {{MUST_CUSTOMIZE}} markers. Run:"
echo "  '$KIT_ROOT/bootstrap/check-must-customize.sh' '$TARGET'"
echo "to see what still needs filling in."
