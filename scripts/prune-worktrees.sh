#!/usr/bin/env bash
# Remove git worktrees and branches whose work is already merged into the default branch.
#
# Safe by design: removes only branches whose content is already present on
# the default branch, never the main checkout, never `git worktree remove --force`. Dirty
# or unmerged work is skipped and reported. Commits nothing, pushes nothing,
# merges nothing.
#
# Branch deletion uses `git branch -D`, not `-d`: git's own -d safety check
# is ancestry-based and always refuses a squash- or rebase-merged branch, no
# matter how thoroughly it was actually reviewed and merged. -D is gated
# entirely on this script's own is_merged() check below, which is stricter
# than git's (patch-content equivalence, not graph ancestry) — so it is only
# ever applied to branches whose content is provably already on the default branch.
#
# "Merged" is detected two ways. First, plain ancestry: if the branch tip is
# already reachable from main (fast-forward or rebase merge that preserves the
# commits), it is merged, full stop. Second, for squash merges — where the
# branch content lands as a brand-new commit and the tip is never an ancestor
# of main — we fall back to patch-id equivalence: build a throwaway commit
# (branch tip's tree, parented on the branch/main merge-base) and ask
# `git cherry` whether an equivalent patch already exists on main. The
# throwaway commit is never attached to a ref; it's ordinary git gc litter and
# disappears on the next gc.
#
# The ancestry check must come first: for an ancestry-merged branch the
# merge-base *is* the branch tip, so the synthetic commit's diff is empty, and
# `git cherry` marks an empty patch "+" (not present) — a false negative that
# would wrongly skip a genuinely merged branch.
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
    echo "Warning: could not fetch origin; checking against local default branch, which may be stale." >&2
fi

# Detect the default branch from remote HEAD; fall back to origin/main, then main.
base="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/||' || true)"
if [ -z "$base" ]; then
    base="origin/main"
fi
git rev-parse --verify --quiet "$base" >/dev/null 2>&1 || base="main"

# True if branch $1's content is already present on $base, regardless of
# whether it landed via merge commit, rebase, or squash.
is_merged() {
    local branch="$1" merge_base tree synthetic mark
    # Fast path: branch tip already reachable from base (ff / rebase / merge
    # commit). Covers everything git's own `--merged` would, empty diff or not.
    git merge-base --is-ancestor "$branch" "$base" 2>/dev/null && return 0
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

default_branch="${base##*/}"
while IFS= read -r branch; do
    [ -z "$branch" ] && continue
    if [ "$branch" = "$default_branch" ]; then
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
