# Project-specific invariants

The load-bearing rules every agent enforces. This is the single authoritative source — the feature driver pastes the invariant list into every worker brief (`## Project invariants`); spec-reviewer and pr-reviewer also read it directly. Reasoning lives in `docs/decisions.md` (see decisions 2 and 3).

Rules for this list — reviewers flag any edit that breaks them:

- One line per invariant: imperative, concrete, checkable from the diff alone. Rationale goes in `docs/decisions.md`, never here.
- Hard cap 10 invariants. Overflow is a convention — move it to the matching `conventions/*.md` file.
- No rule that is derivable from code, the toolchain, or a doc agents already load; no duplicates — point at the single source.
- Prefer mechanical enforcement: anything a hook, lint, or CI check can enforce (pattern: `scripts/hooks/worktree-path-guard.sh`) is implemented there, leaving at most one line naming the check.

- Runtime code and its tests are Python stdlib only — no third-party imports, no dependency manifest.
- Machine-level state lives outside every checkout: the run-journal db path comes from `RUN_JOURNAL_DB` (default `~/.agent-journal/runs.db`), never repo-relative; tests must point `RUN_JOURNAL_DB` at a temp path.
- Workflow files under `.claude/` name toolchain facts only as `${VAR}` resolved from `.claude/project.md` — never hardcoded.
