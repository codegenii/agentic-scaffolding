#!/usr/bin/env bash
# Remove git worktrees and branches whose work is already merged into main.
#
# Safe by design: removes only branches whose content is already present on
# main, never the main checkout, never `git worktree remove --force`. Dirty
# or unmerged work is skipped and reported. Commits nothing, pushes nothing,
# merges nothing.
#
# Branch deletion uses `git branch -D`, not `-d`: git's own -d safety check
# is ancestry-based and always refuses a squash- or rebase-merged branch, no
# matter how thoroughly it was actually reviewed and merged. -D is gated
# entirely on this script's own is_merged() check below, which is stricter
# than git's (patch-content equivalence, not graph ancestry) — so it is only
# ever applied to branches whose content is provably already on main.
#
# "Merged" is detected by patch-id equivalence, not commit ancestry: this repo
# integrates PRs via squash/rebase merge, so plain `git branch --merged`
# (ancestry-based) never matches — the branch tip commit is never an ancestor
# of main once its content lands as a brand-new squash commit. For each branch
# we build a throwaway commit (branch tip's tree, parented on the branch/main
# merge-base) and ask `git cherry` whether an equivalent patch already exists
# on main. The throwaway commit is never attached to a ref; it's ordinary git
# gc litter and disappears on the next gc.
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

if ! git fetch origin --quiet 2>/dev/null; then
    echo "Warning: could not fetch origin; checking against local main, which may be stale." >&2
fi
base="origin/main"
git rev-parse --verify --quiet origin/main >/dev/null 2>&1 || base="main"

# True if branch $1's content is already present on $base, regardless of
# whether it landed via merge commit, rebase, or squash.
is_merged() {
    local branch="$1" merge_base tree synthetic mark
    merge_base="$(git merge-base "$base" "$branch" 2>/dev/null)" || return 1
    tree="$(git rev-parse "$branch^{tree}" 2>/dev/null)" || return 1
    synthetic="$(git commit-tree "$tree" -p "$merge_base" -m _prune-check)"
    mark="$(git cherry "$base" "$synthetic" | cut -c1)"
    [ "$mark" = "-" ]
}

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
    if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
        continue
    fi
    if ! is_merged "$branch"; then
        continue
    fi
    if out="$(git branch -D "$branch" 2>&1)"; then
        removed+=("branch $branch")
    else
        skipped+=("branch $branch — $out")
    fi
done < <(git for-each-ref refs/heads --format='%(refname:short)')

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
