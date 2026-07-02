#!/usr/bin/env bash
# sync-worktree-permissions.sh — promote Claude Code permissions approved in a
# worktree back into the main checkout's settings.local.json, so later worktrees
# (via setup-worktree.sh) inherit them.
#
# The inverse of setup-worktree.sh. Run it from a finished worktree before the
# branch is merged and the worktree pruned.
#
# Usage:
#   cd /path/to/worktree && sync-worktree-permissions.sh
#   sync-worktree-permissions.sh /path/to/worktree

set -euo pipefail

log() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

TARGET_DIR="${1:-$PWD}"
[[ -d "$TARGET_DIR" ]] || die "$TARGET_DIR is not a directory"
cd "$TARGET_DIR"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "$TARGET_DIR is not inside a git working tree"

# `git worktree list` always lists the main worktree first.
read -r _ MAIN_DIR < <(git worktree list --porcelain)
[[ -n "${MAIN_DIR:-}" ]] || die "could not determine main worktree"

CURRENT_REAL=$(pwd -P)
MAIN_REAL=$(cd "$MAIN_DIR" && pwd -P)
[[ "$CURRENT_REAL" != "$MAIN_REAL" ]] \
  || die "refusing to sync the main worktree into itself ($MAIN_REAL)"

# SRC is this worktree, DEST is the main checkout — the inverse of setup-worktree.sh.
SRC="$CURRENT_REAL/.claude/settings.local.json"
DEST_DIR="$MAIN_REAL/.claude"
DEST="$DEST_DIR/settings.local.json"

[[ -f "$SRC" ]] || die "no $SRC in this worktree — nothing to sync back"
command -v jq >/dev/null 2>&1 || die "jq is required to sync permissions"
jq -e . "$SRC" >/dev/null 2>&1 || die "$SRC is not valid JSON"

mkdir -p "$DEST_DIR"
# Treat a missing main file as an empty object, so one path handles seed + merge.
[[ -f "$DEST" ]] || echo '{}' >"$DEST"
jq -e . "$DEST" >/dev/null 2>&1 || die "$DEST is not valid JSON"

# Report exactly which rules this sync promotes — rules in the worktree but not
# yet in main. Transparency: the main allowlist only ever grows here.
promoted=$(jq -rs '
  (.[0].permissions // {}) as $src | (.[1].permissions // {}) as $dst |
  [ (($src.allow // []) - ($dst.allow // [])) | .[] | "  + allow " + . ],
  [ (($src.deny  // []) - ($dst.deny  // [])) | .[] | "  + deny "  + . ],
  [ (($src.ask   // []) - ($dst.ask   // [])) | .[] | "  + ask "   + . ]
  | .[]' "$SRC" "$DEST")

if [[ -z "$promoted" ]]; then
  log "no new permissions to promote — main already covers this worktree"
  exit 0
fi
log "promoting to $DEST:"
log "$promoted"

# Merge into main: main (dst) wins scalar conflicts; allow/deny/ask are unioned.
TMP=""
trap '[[ -n "$TMP" && -f "$TMP" ]] && rm -f "$TMP"; true' EXIT
TMP=$(mktemp "$DEST_DIR/.settings.local.json.XXXXXX")

jq -s '
  .[0] as $src | .[1] as $dst |
  ($src * $dst)
  | .permissions = (($src.permissions // {}) * ($dst.permissions // {}))
  | .permissions.allow = ((($src.permissions.allow // []) + ($dst.permissions.allow // [])) | unique)
  | .permissions.deny  = ((($src.permissions.deny  // []) + ($dst.permissions.deny  // [])) | unique)
  | .permissions.ask   = ((($src.permissions.ask   // []) + ($dst.permissions.ask   // [])) | unique)
' "$SRC" "$DEST" >"$TMP"

jq -e . "$TMP" >/dev/null 2>&1 || die "merge produced invalid JSON; aborting"
mv "$TMP" "$DEST"
TMP=""
log "synced permissions back to main worktree"
