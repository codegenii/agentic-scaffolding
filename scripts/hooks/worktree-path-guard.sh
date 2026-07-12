#!/usr/bin/env bash
# worktree-path-guard.sh — PreToolUse hook for Edit/Write/Read/NotebookEdit.
#
# Two checks, depending on where the session runs:
#
#  - Linked worktree: deny a file path that resolves into a *different*
#    checkout of this repo (the main checkout or a sibling worktree) — the
#    classic mistake of building absolute paths from the main checkout.
#    Paths inside the current worktree and paths outside the repo entirely
#    (temp dirs, etc.) pass.
#
#  - Main checkout on the default branch: writes (Edit/Write/NotebookEdit)
#    to non-ignored files under the repo root surface a confirmation
#    prompt — task work belongs in a worktree (/new-chore, /new-feature).
#    Reads, gitignored paths, and paths outside the repo pass, as does
#    everything when the checkout sits on a non-default branch.
#
# Fails open: guard plumbing must never block legitimate file operations.
#
# stdin:  PreToolUse hook JSON; reads .tool_name and .tool_input paths.
# stdout: {"hookSpecificOutput":{"permissionDecision":"deny"|"ask",...}} on a hit.

set -u

command -v jq >/dev/null 2>&1 || exit 0
command -v realpath >/dev/null 2>&1 || exit 0

input=$(cat) || exit 0
tool_name=$(jq -r '.tool_name // empty' <<<"$input" 2>/dev/null) || exit 0
fpath=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$input" 2>/dev/null) || exit 0
[ -n "$fpath" ] || exit 0

git_dir=$(git rev-parse --git-dir 2>/dev/null) || exit 0
git_common=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0

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

if [ "$git_dir" = "$git_common" ]; then
  # Main checkout. Guard only writes, and only on the default branch —
  # sessions that branched first are doing it right.
  case $tool_name in Edit | Write | NotebookEdit) ;; *) exit 0 ;; esac
  default_branch=main
  db=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null) \
    && default_branch=${db#origin/}
  [ "$(git branch --show-current 2>/dev/null)" = "$default_branch" ] || exit 0
  case $cand_f in
    "$top_f" | "$top_f"/*) ;;
    *) exit 0 ;;
  esac
  git check-ignore -q -- "$cand" 2>/dev/null && exit 0
  rel=${cand:$((${#top} + 1))}
  jq -cn --arg reason "Write to './$rel' targets the shared main checkout on '$default_branch'. Task work belongs in a worktree — use /new-chore or /new-feature. Allow only if this is deliberate integration-tree maintenance." \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $reason}}'
  exit 0
fi

# Linked worktree from here on.
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
