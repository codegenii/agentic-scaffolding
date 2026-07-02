#!/usr/bin/env bash
# Remove git worktrees and branches whose work is already merged into main.
#
# Safe by design: removes only branches merged into main, never the main
# checkout, never --force, never -D. Dirty or unmerged work is skipped and
# reported. Commits nothing, pushes nothing, merges nothing.
#
# Run from the main checkout:  ./scripts/prune-worktrees.sh
set -euo pipefail

# --- Step 1: survey ---------------------------------------------------------

# Parse `git worktree list`; the first entry is always the main checkout.
paths=() branches=()
while IFS= read -r line; do
    case "$line" in
        worktree\ *) paths+=("${line#worktree }"); branches+=("") ;;
        branch\ refs/heads/*) branches[${#branches[@]}-1]="${line#branch refs/heads/}" ;;
    esac
done < <(git worktree list --porcelain)

main_path="${paths[0]}"
top_level="$(git rev-parse --show-toplevel)"
if [ "$top_level" != "$main_path" ]; then
    echo "Run this from the main checkout ($main_path), not a worktree." >&2
    exit 1
fi

git fetch origin --quiet 2>/dev/null || true
base="origin/main"
git rev-parse --verify --quiet origin/main >/dev/null 2>&1 || base="main"

merged="$(git branch --merged "$base" --format='%(refname:short)')"
is_merged() { grep -qxF "$1" <<<"$merged"; }

removed=() skipped=()

# --- Step 2: remove merged worktrees ---------------------------------------

for i in "${!paths[@]}"; do
    [ "$i" -eq 0 ] && continue
    path="${paths[$i]}" branch="${branches[$i]}"
    if [ -z "$branch" ]; then
        skipped+=("worktree $path — detached HEAD, left in place"); continue
    fi
    if ! is_merged "$branch"; then
        skipped+=("worktree $path [$branch] — not merged, still under review"); continue
    fi
    if out="$(git worktree remove "$path" 2>&1)"; then
        removed+=("worktree $path [$branch]")
    else
        skipped+=("worktree $path [$branch] — $out")
    fi
done

# --- Step 3: delete merged branches ----------------------------------------

while IFS= read -r branch; do
    [ -z "$branch" ] && continue
    [ "$branch" = "main" ] || [ "$branch" = "master" ] && continue
    if out="$(git branch -d "$branch" 2>&1)"; then
        removed+=("branch $branch")
    else
        skipped+=("branch $branch — $out")
    fi
done <<<"$merged"

# --- Step 4: report ---------------------------------------------------------

git worktree prune

echo
if [ ${#removed[@]} -gt 0 ]; then
    echo "Removed:"
    printf '  %s\n' "${removed[@]}"
else
    echo "Nothing to remove — no merged worktrees or branches."
fi
if [ ${#skipped[@]} -gt 0 ]; then
    echo
    echo "Skipped (needs review):"
    printf '  %s\n' "${skipped[@]}"
fi
