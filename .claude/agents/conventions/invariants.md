# Project-specific invariants

The load-bearing rules every agent enforces. This is the single authoritative source — loaded by implementer, test-writer, spec-reviewer, and pr-reviewer alongside their role file. Reasoning lives in `docs/decisions.md` (see decision 2).

Rules for this list — reviewers flag any edit that breaks them:

- One line per invariant: imperative, concrete, checkable from the diff alone. Rationale goes in `docs/decisions.md`, never here.
- Hard cap 10 invariants. Overflow is a convention — move it to the matching `conventions/*.md` file.
- No rule that is derivable from code, the toolchain, or a doc agents already load; no duplicates — point at the single source.
- Prefer mechanical enforcement: anything a hook, lint, or CI check can enforce (pattern: `scripts/hooks/worktree-path-guard.sh`) is implemented there, leaving at most one line naming the check.

<!--
`/init-project` seeds the list below from your answers; delete this comment
then. Examples of the right shape (from a real project):

- The coverage analyzer and the planner contain no LLM calls — deterministic.
- Every generated artifact cites the spec clause it satisfies.
- The four pluggable interfaces are the only extension points. Do not widen, do not bypass.
- Default-mode code paths must work offline.
- Runtime boundary — files in, files out. The tool never spawns processes, never
  runs git, never manages external services, never calls the system under test.
-->

- <your first invariant>
- <your second invariant>
