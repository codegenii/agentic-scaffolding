#!/usr/bin/env bash
# worktree-path-guard.sh — PreToolUse hook for Edit/Write/Read/NotebookEdit.
#
# In a linked worktree, deny a file path that resolves into a *different*
# checkout of this repo (the main checkout or a sibling worktree) — the
# classic mistake of building absolute paths from the main checkout. Paths
# inside the current worktree and paths outside the repo entirely (temp
# dirs, etc.) pass. In the main checkout the guard is inactive.
#
# Fails open: guard plumbing must never block legitimate file operations.
#
# stdin:  PreToolUse hook JSON; reads .tool_input.file_path / .notebook_path.
# stdout: {"hookSpecificOutput":{"permissionDecision":"deny",...}} on violation.

set -u

command -v jq >/dev/null 2>&1 || exit 0
command -v realpath >/dev/null 2>&1 || exit 0

fpath=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' 2>/dev/null) || exit 0
[ -n "$fpath" ] || exit 0

# Only linked worktrees are guarded; in the main checkout git-dir and
# git-common-dir coincide.
git_dir=$(git rev-parse --git-dir 2>/dev/null) || exit 0
git_common=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
[ "$git_dir" != "$git_common" ] || exit 0

# Canonicalize to one comparable form. -m allows not-yet-existing targets
# (Write); backslashes become slashes first so realpath doesn't take them
# as literal characters. On Windows, realpath alone is inconsistent — it
# yields /c/... for relative inputs but leaves C:/... untouched — so route
# through cygpath to force a single form.
HAVE_CYGPATH=""
command -v cygpath >/dev/null 2>&1 && HAVE_CYGPATH=1
canon() {
  local p=${1//\\//}
  if [ -n "$HAVE_CYGPATH" ]; then p=$(cygpath -u "$p" 2>/dev/null) || return 1; fi
  p=$(realpath -m "$p" 2>/dev/null) || return 1
  if [ -n "$HAVE_CYGPATH" ]; then p=$(cygpath -m "$p" 2>/dev/null) || return 1; fi
  printf '%s\n' "$p"
}

# Case-fold comparisons on case-insensitive filesystems.
case ${OSTYPE:-} in
  msys* | cygwin* | darwin*) fold() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; } ;;
  *) fold() { printf '%s' "$1"; } ;;
esac

top=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
top=$(canon "$top")
cand=$(canon "$fpath")
[ -n "$top" ] && [ -n "$cand" ] || exit 0
top_f=$(fold "$top")
cand_f=$(fold "$cand")

# Inside the current worktree: fine. Checked before the other-checkout scan
# because worktrees may live under the main checkout (.claude/worktrees/).
case $cand_f in
  "$top_f" | "$top_f"/*) exit 0 ;;
esac

# Inside another checkout of this repo? Prefer the longest matching root so
# a sibling worktree under the main checkout is named, not the main itself.
best=""
while IFS= read -r line; do
  case $line in "worktree "*) ;; *) continue ;; esac
  wt=$(canon "${line#worktree }")
  [ -n "$wt" ] || continue
  wt_f=$(fold "$wt")
  [ "$wt_f" = "$top_f" ] && continue
  case $cand_f in
    "$wt_f" | "$wt_f"/*) [ ${#wt} -gt ${#best} ] && best=$wt ;;
  esac
done < <(git worktree list --porcelain 2>/dev/null)

[ -n "$best" ] || exit 0

rel=${cand:$((${#best} + 1))}
jq -cn --arg reason "'$fpath' resolves into a different checkout of this repo ($best), not this session's worktree ($top). Build the path from this worktree's root instead: ./$rel" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
exit 0
