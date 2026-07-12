#!/usr/bin/env bash
# install.sh — bootstrap this Claude Code workflow template into a target repo.
#
# Usage:
#   ./scripts/install.sh [--force] /path/to/target-repo
#
# Run from a checkout of this template. Copies every file listed in
# scripts/template-manifest.txt into TARGET, using each file's class to
# decide the copy policy:
#   - core:         always installed; on re-run, overwritten only with
#                   --force if the target's copy has diverged.
#   - stub:         installed only if absent in the target; if present, left
#                   untouched (content comparison irrelevant). Exception:
#                   .gitignore gets two required lines appended if missing.
#   - template-dev: never copied — template development scaffolding only.
#
# Safe to re-run: an unchanged target with the same template commit is left
# alone and reported "already up to date". Provenance (template commit +
# install date) is recorded in $TARGET/.claude/template-version.
set -euo pipefail

log()  { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'USAGE' >&2
Usage: ./scripts/install.sh [--force] /path/to/target-repo
USAGE
}

# --- Resolve template root --------------------------------------------------

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
TEMPLATE_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
MANIFEST="$SCRIPT_DIR/template-manifest.txt"

[[ -f "$MANIFEST" ]] \
  || die "template-manifest.txt not found next to this script — run this from a checkout of the template"

# --- Parse args --------------------------------------------------------------

FORCE=0
POSITIONAL=()
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) POSITIONAL+=("$arg") ;;
  esac
done

if [[ ${#POSITIONAL[@]} -eq 0 ]]; then
  usage
  die "no target repository given"
fi
[[ ${#POSITIONAL[@]} -eq 1 ]] || die "too many arguments — expected exactly one target repo path"
TARGET_ARG="${POSITIONAL[0]}"

# --- Validate target ---------------------------------------------------------

[[ -d "$TARGET_ARG" ]] || die "$TARGET_ARG is not a directory"
TARGET=$(cd "$TARGET_ARG" && pwd -P)

git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "$TARGET is not a git repository — run 'git init' there first"

[[ "$TARGET" != "$TEMPLATE_ROOT" ]] \
  || die "refusing to install the template into itself ($TEMPLATE_ROOT)"

# --- Copy bookkeeping ---------------------------------------------------------

installed=()
skipped_existing=()
APPENDED_COUNT=0

chmod_if_script() {
  case "$1" in
    scripts/*) chmod +x "$TARGET/$1" ;;
  esac
}

install_core() {
  local rel="$1" src="$TEMPLATE_ROOT/$1" dest="$TARGET/$1"
  [[ -f "$src" ]] || die "template checkout is broken: missing core file $rel"
  mkdir -p "$(dirname "$dest")"
  if [[ -e "$dest" ]]; then
    if cmp -s "$src" "$dest"; then
      return 0 # identical — nothing to do
    fi
    if [[ $FORCE -eq 1 ]]; then
      cp "$src" "$dest"
      chmod_if_script "$rel"
      log "overwrote (--force): $rel"
      installed+=("$rel")
    else
      warn "skipping $rel — differs from template (re-run with --force to overwrite)"
      skipped_existing+=("$rel")
    fi
  else
    cp "$src" "$dest"
    chmod_if_script "$rel"
    log "installed: $rel"
    installed+=("$rel")
  fi
}

# Append $2 to file $1 if not already present as an exact line, fixing up a
# missing trailing newline first. Increments APPENDED_COUNT on each append.
append_line_once() {
  local dest="$1" line="$2"
  grep -qxF "$line" "$dest" 2>/dev/null && return 0
  if [[ -s "$dest" ]] && [[ -n "$(tail -c1 "$dest")" ]]; then
    printf '\n' >> "$dest"
  fi
  printf '%s\n' "$line" >> "$dest"
  APPENDED_COUNT=$((APPENDED_COUNT + 1))
}

install_gitignore() {
  local rel="$1" src="$TEMPLATE_ROOT/$1" dest="$TARGET/$1"
  if [[ ! -e "$dest" ]]; then
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    log "installed: $rel"
    installed+=("$rel")
    return 0
  fi
  local before=$APPENDED_COUNT
  append_line_once "$dest" ".claude/settings.local.json"
  append_line_once "$dest" ".claude/worktrees/"
  if [[ $APPENDED_COUNT -gt $before ]]; then
    log "updated: $rel (appended $((APPENDED_COUNT - before)) line(s))"
  else
    log "exists, left untouched: $rel"
    skipped_existing+=("$rel")
  fi
}

install_stub() {
  local rel="$1" src="$TEMPLATE_ROOT/$1" dest="$TARGET/$1"
  [[ -f "$src" ]] || die "template checkout is broken: missing stub file $rel"
  if [[ "$rel" == ".gitignore" ]]; then
    install_gitignore "$rel"
    return 0
  fi
  if [[ -e "$dest" ]]; then
    log "exists, left untouched: $rel"
    skipped_existing+=("$rel")
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  chmod_if_script "$rel"
  log "installed: $rel"
  installed+=("$rel")
}

# --- Walk the manifest ---------------------------------------------------------

while IFS= read -r rawline || [[ -n "$rawline" ]]; do
  [[ -z "$rawline" ]] && continue
  case "$rawline" in
    \#*) continue ;;
  esac
  class="${rawline%%$'\t'*}"
  path="${rawline#*$'\t'}"
  [[ -n "$path" && "$path" != "$rawline" ]] || die "malformed manifest line: $rawline"

  # Never copy the manifest itself, regardless of class.
  [[ "$path" == "scripts/template-manifest.txt" ]] && continue

  case "$class" in
    core) install_core "$path" ;;
    stub) install_stub "$path" ;;
    template-dev) : ;;
    *) die "unknown manifest class '$class' for $path" ;;
  esac
done < "$MANIFEST"

# --- Provenance --------------------------------------------------------------

TEMPLATE_HEAD=$(git -C "$TEMPLATE_ROOT" rev-parse HEAD 2>/dev/null) \
  || { warn "could not determine template HEAD commit"; TEMPLATE_HEAD="unknown"; }

VERSION_FILE="$TARGET/.claude/template-version"
NEED_VERSION_WRITE=0

if [[ ${#installed[@]} -gt 0 || $APPENDED_COUNT -gt 0 ]]; then
  NEED_VERSION_WRITE=1
elif [[ ! -f "$VERSION_FILE" ]]; then
  NEED_VERSION_WRITE=1
else
  recorded_commit=$(grep -m1 '^commit ' "$VERSION_FILE" | cut -d' ' -f2- || true)
  [[ "$recorded_commit" == "$TEMPLATE_HEAD" ]] || NEED_VERSION_WRITE=1
fi

if [[ $NEED_VERSION_WRITE -eq 1 ]]; then
  mkdir -p "$TARGET/.claude"
  {
    printf 'commit %s\n' "$TEMPLATE_HEAD"
    printf 'installed %s\n' "$(date +%F)"
  } > "$VERSION_FILE"
fi

# --- Summary -------------------------------------------------------------------

log ""
log "Installed:            ${#installed[@]}"
log "Skipped (pre-existing): ${#skipped_existing[@]}"
log "Appended:              $APPENDED_COUNT"
log ""
if [[ ${#installed[@]} -eq 0 && $APPENDED_COUNT -eq 0 ]]; then
  log "Already up to date (template commit $TEMPLATE_HEAD)."
else
  log "Template installed/updated (commit $TEMPLATE_HEAD)."
fi
log ""
log "Next: open Claude Code in $TARGET and run /init-project"

exit 0
