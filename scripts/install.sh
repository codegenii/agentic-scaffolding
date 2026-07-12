#!/usr/bin/env bash
# install.sh — bootstrap this Claude Code workflow template into a target repo,
# and update a previous install by re-running from a newer template checkout.
#
# Usage:
#   ./scripts/install.sh [--force] /path/to/target-repo
#
# Run from a checkout of this template. Copies every file listed in
# scripts/template-manifest.txt into TARGET, using each file's class to
# decide the copy policy:
#   - core:         always installed; on re-run, a copy the target has not
#                   modified is updated in place, a locally modified copy is
#                   kept unless --force.
#   - stub:         installed only if absent in the target; if present, left
#                   untouched (content comparison irrelevant). Exception:
#                   .gitignore gets two required lines appended if missing.
#   - template-dev: never copied — template development scaffolding only.
#
# An update run (the target has .claude/template-version) prints a pre-copy
# summary — recorded commit -> new commit, which core files change — before
# touching anything. Provenance (template commit + install date) is recorded
# in $TARGET/.claude/template-version. The update flow is documented in the
# installed CONTRIBUTING.md ("Updating the workflow").
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

# --- Provenance of the previous install ---------------------------------------

TEMPLATE_HEAD=$(git -C "$TEMPLATE_ROOT" rev-parse HEAD 2>/dev/null) \
  || { warn "could not determine template HEAD commit"; TEMPLATE_HEAD="unknown"; }

VERSION_FILE="$TARGET/.claude/template-version"
RECORDED_COMMIT=""
if [[ -f "$VERSION_FILE" ]]; then
  RECORDED_COMMIT=$(grep -m1 '^commit ' "$VERSION_FILE" | cut -d' ' -f2- || true)
fi

if [[ -n "$RECORDED_COMMIT" && "$RECORDED_COMMIT" != "unknown" ]] \
   && ! git -C "$TEMPLATE_ROOT" cat-file -e "$RECORDED_COMMIT^{commit}" 2>/dev/null; then
  warn "recorded template commit $RECORDED_COMMIT is not in this checkout — every changed core file will look locally modified (review, then --force)"
fi

# All content comparisons ignore CR line endings: with `* text=auto`, a Windows
# checkout materializes CRLF in the working tree while git blobs store LF, and
# ending differences must never read as content differences.
norm() { sed 's/\r$//' "$1"; }

same_content() { cmp -s <(norm "$1") <(norm "$2"); }

# Does target file $2 match manifest path $1's content at the recorded template
# commit? A match means the target never modified its copy, so any difference
# from the new template is template progress and safe to take. Uses ls-tree +
# cat-file, not "commit:path" — MSYS bash mangles the colon form into a
# Windows path.
matches_recorded() {
  local rel="$1" dest="$2" blob
  [[ -n "$RECORDED_COMMIT" && "$RECORDED_COMMIT" != "unknown" ]] || return 1
  blob=$(git -C "$TEMPLATE_ROOT" ls-tree -r "$RECORDED_COMMIT" -- "$rel" 2>/dev/null | awk '{print $3}')
  [[ -n "$blob" ]] || return 1
  git -C "$TEMPLATE_ROOT" cat-file blob "$blob" 2>/dev/null | sed 's/\r$//' | cmp -s - <(norm "$dest")
}

# --- Read the manifest ---------------------------------------------------------

MANIFEST_CLASSES=()
MANIFEST_PATHS=()
while IFS= read -r rawline || [[ -n "$rawline" ]]; do
  rawline="${rawline%$'\r'}"
  [[ -z "$rawline" ]] && continue
  case "$rawline" in
    \#*) continue ;;
  esac
  class="${rawline%%$'\t'*}"
  path="${rawline#*$'\t'}"
  [[ -n "$path" && "$path" != "$rawline" ]] || die "malformed manifest line: $rawline"

  # Never copy the manifest itself, regardless of class.
  [[ "$path" == "scripts/template-manifest.txt" ]] && continue

  # /init-project deletes itself after first-time setup — never resurrect it.
  if [[ "$path" == ".claude/commands/init-project.md" && -n "$RECORDED_COMMIT" && ! -e "$TARGET/$path" ]]; then
    log "skipped: $path (self-destructed after /init-project)"
    continue
  fi

  case "$class" in
    core|stub) MANIFEST_CLASSES+=("$class"); MANIFEST_PATHS+=("$path") ;;
    template-dev) : ;;
    *) die "unknown manifest class '$class' for $path" ;;
  esac
done < "$MANIFEST"

[[ ${#MANIFEST_PATHS[@]} -gt 0 ]] || die "manifest lists nothing to install"

# --- Pre-copy summary (update runs) --------------------------------------------

core_add=()      # not in the target yet
core_update=()   # differ, unmodified locally — updated in place
core_modified=() # differ, locally modified — kept unless --force

for i in "${!MANIFEST_PATHS[@]}"; do
  [[ "${MANIFEST_CLASSES[$i]}" == "core" ]] || continue
  rel="${MANIFEST_PATHS[$i]}"
  src="$TEMPLATE_ROOT/$rel"
  dest="$TARGET/$rel"
  [[ -f "$src" ]] || die "template checkout is broken: missing core file $rel"
  if [[ ! -e "$dest" ]]; then
    core_add+=("$rel")
  elif same_content "$src" "$dest"; then
    :
  elif matches_recorded "$rel" "$dest"; then
    core_update+=("$rel")
  else
    core_modified+=("$rel")
  fi
done

if [[ -n "$RECORDED_COMMIT" ]]; then
  log "Updating template: $RECORDED_COMMIT -> $TEMPLATE_HEAD"
  if [[ ${#core_add[@]} -eq 0 && ${#core_update[@]} -eq 0 && ${#core_modified[@]} -eq 0 ]]; then
    log "  core files: all up to date"
  fi
  if [[ ${#core_update[@]} -gt 0 ]]; then
    log "  will update (unmodified locally):"
    for rel in "${core_update[@]}"; do log "    $rel"; done
  fi
  if [[ ${#core_add[@]} -gt 0 ]]; then
    log "  will add (new in template):"
    for rel in "${core_add[@]}"; do log "    $rel"; done
  fi
  if [[ ${#core_modified[@]} -gt 0 ]]; then
    if [[ $FORCE -eq 1 ]]; then
      log "  will overwrite (--force, locally modified):"
    else
      log "  will keep (locally modified — re-run with --force to overwrite):"
    fi
    for rel in "${core_modified[@]}"; do log "    $rel"; done
  fi
  log ""
fi

# --- Copy bookkeeping ---------------------------------------------------------

installed=()
skipped_existing=()
skipped_modified=()
APPENDED_COUNT=0

chmod_if_script() {
  case "$1" in
    scripts/*) chmod +x "$TARGET/$1" ;;
  esac
}

install_core() {
  local rel="$1" src="$TEMPLATE_ROOT/$1" dest="$TARGET/$1"
  mkdir -p "$(dirname "$dest")"
  if [[ -e "$dest" ]]; then
    if same_content "$src" "$dest"; then
      return 0 # identical — nothing to do
    fi
    if [[ $FORCE -eq 1 ]]; then
      cp "$src" "$dest"
      chmod_if_script "$rel"
      log "overwrote (--force): $rel"
      installed+=("$rel")
    elif matches_recorded "$rel" "$dest"; then
      cp "$src" "$dest"
      chmod_if_script "$rel"
      log "updated: $rel"
      installed+=("$rel")
    else
      warn "skipping $rel — locally modified (re-run with --force to overwrite)"
      skipped_modified+=("$rel")
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
  grep -qxF -e "$line" -e "$line"$'\r' "$dest" 2>/dev/null && return 0
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

for i in "${!MANIFEST_PATHS[@]}"; do
  case "${MANIFEST_CLASSES[$i]}" in
    core) install_core "${MANIFEST_PATHS[$i]}" ;;
    stub) install_stub "${MANIFEST_PATHS[$i]}" ;;
  esac
done

# --- Provenance --------------------------------------------------------------

NEED_VERSION_WRITE=0
if [[ ${#installed[@]} -gt 0 || $APPENDED_COUNT -gt 0 ]]; then
  NEED_VERSION_WRITE=1
elif [[ ! -f "$VERSION_FILE" ]]; then
  NEED_VERSION_WRITE=1
elif [[ "$RECORDED_COMMIT" != "$TEMPLATE_HEAD" ]]; then
  NEED_VERSION_WRITE=1
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
log "Installed/updated:          ${#installed[@]}"
log "Skipped (pre-existing):     ${#skipped_existing[@]}"
log "Skipped (locally modified): ${#skipped_modified[@]}"
log "Appended:                   $APPENDED_COUNT"
log ""
if [[ ${#installed[@]} -eq 0 && $APPENDED_COUNT -eq 0 ]]; then
  if [[ ${#skipped_modified[@]} -gt 0 ]]; then
    log "Nothing copied (template commit $TEMPLATE_HEAD)."
  else
    log "Already up to date (template commit $TEMPLATE_HEAD)."
  fi
else
  log "Template installed/updated (commit $TEMPLATE_HEAD)."
fi
if [[ ${#skipped_modified[@]} -gt 0 ]]; then
  log "Locally modified core files were kept — reconcile them by hand, or re-run with --force to overwrite."
fi
log ""
if [[ -n "$RECORDED_COMMIT" ]]; then
  log "Next: review the changes in $TARGET (git diff), then commit."
else
  log "Next: open Claude Code in $TARGET and run /init-project"
fi

exit 0
