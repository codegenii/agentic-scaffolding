#!/usr/bin/env bash
# setup-worktree.sh — propagate Claude Code local permissions into a new worktree.
#
# Usage:
#   cd /path/to/new-worktree && setup-worktree.sh
#   setup-worktree.sh /path/to/new-worktree

set -euo pipefail

log()  { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

TARGET_DIR="${1:-$PWD}"
[[ -d "$TARGET_DIR" ]] || die "$TARGET_DIR is not a directory"
cd "$TARGET_DIR"

# Must be inside a git worktree.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "$TARGET_DIR is not inside a git working tree"

# Resolve the main worktree. The main is the one whose .git is a *directory*;
# linked worktrees have a .git *file* pointing at the main's gitdir.
# We iterate `git worktree list --porcelain` and pick the entry where
# "$worktree/.git" is a directory.
MAIN_DIR=""
while IFS= read -r line; do
  case "$line" in
    "worktree "*)
      candidate="${line#worktree }"
      if [[ -d "$candidate/.git" ]]; then
        MAIN_DIR="$candidate"
        break
      fi
      ;;
  esac
done < <(git worktree list --porcelain)

[[ -n "$MAIN_DIR" ]] || die "could not determine main worktree"

CURRENT_REAL=$(pwd -P)
MAIN_REAL=$(cd "$MAIN_DIR" && pwd -P)

[[ "$CURRENT_REAL" != "$MAIN_REAL" ]] \
  || die "refusing to run inside the main worktree ($MAIN_REAL)"

SRC="$MAIN_REAL/.claude/settings.local.json"
DEST_DIR=".claude"
DEST="$DEST_DIR/settings.local.json"

[[ -f "$SRC" ]] || die "no $SRC to propagate"

# Validate source is parseable JSON before doing anything.
if command -v jq >/dev/null 2>&1; then
  jq -e . "$SRC" >/dev/null 2>&1 || die "$SRC is not valid JSON"
fi

mkdir -p "$DEST_DIR"

# Always write through a temp file in the same directory for atomic rename.
TMP=""
cleanup() { if [[ -n "$TMP" && -f "$TMP" ]]; then rm -f "$TMP"; fi; }
trap cleanup EXIT INT TERM

TMP=$(mktemp "$DEST_DIR/.settings.local.json.XXXXXX")

if [[ ! -f "$DEST" ]]; then
  cp "$SRC" "$TMP"
  mv "$TMP" "$DEST"
  TMP=""
  log "copied permissions from main worktree → $DEST"
else
  command -v jq >/dev/null 2>&1 \
    || die "$DEST already exists and jq is not installed for merging"

  jq -e . "$DEST" >/dev/null 2>&1 || die "$DEST exists but is not valid JSON"

  # Merge policy:
  #   - dst wins on any scalar conflict (e.g. defaultMode)
  #   - allow / deny / ask: union, deduped
  #   - keys present only in src are added
  jq -s '
    .[0] as $src | .[1] as $dst |
    ($src * $dst) as $merged |
    $merged
    | .permissions = ((($src.permissions // {}) * ($dst.permissions // {})))
    | .permissions.allow = ((($src.permissions.allow // []) + ($dst.permissions.allow // [])) | unique)
    | .permissions.deny  = ((($src.permissions.deny  // []) + ($dst.permissions.deny  // [])) | unique)
    | .permissions.ask   = ((($src.permissions.ask   // []) + ($dst.permissions.ask   // [])) | unique)
  ' "$SRC" "$DEST" > "$TMP"

  jq -e . "$TMP" >/dev/null 2>&1 || die "merge produced invalid JSON; aborting"

  mv "$TMP" "$DEST"
  TMP=""
  log "merged permissions from main worktree → $DEST"
fi

# Gitignore checks: not tracked AND ignored.
if git ls-files --error-unmatch "$DEST" >/dev/null 2>&1; then
  warn "$DEST is TRACKED by git — remove with: git rm --cached '$DEST'"
elif ! git check-ignore -q "$DEST" 2>/dev/null; then
  warn "$DEST is not gitignored — add '.claude/settings.local.json' to .gitignore"
fi

# Summary.
if command -v jq >/dev/null 2>&1; then
  ALLOW=$(jq '.permissions.allow // [] | length' "$DEST")
  DENY=$(jq  '.permissions.deny  // [] | length' "$DEST")
  ASK=$(jq   '.permissions.ask   // [] | length' "$DEST")
  log "rules: allow=$ALLOW deny=$DENY ask=$ASK"
fi
