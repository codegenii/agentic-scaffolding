# Phase 7 — Mark ready

**Entry gate:** Phase 6 exit gate passed.

1. `gh pr ready`.
2. Run `./scripts/sync-worktree-permissions.sh` to promote permissions approved during this feature into the main checkout.
3. Report the PR URL (`gh pr view --json url -q '.url'`).

Merging is a human decision — stop here. Never merge or close the PR.
