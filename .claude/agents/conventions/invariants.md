# Project-specific invariants

The load-bearing rules every agent enforces. This is the single authoritative source — loaded directly by implementer, test-writer, spec-reviewer, and pr-reviewer alongside their role file. Background reasoning lives in `docs/decisions.md`.

Keep this list short and checkable. Each rule must be something a reviewer can confirm or refute from the diff alone. If a rule needs a paragraph of justification, the justification goes in `docs/decisions.md` and only the rule goes here.

<!--
`/init-project` seeds this from your answers. Replace the examples below with
your project's real invariants, or delete them if you have none yet. Examples
of the shape (from a real project):

- The coverage analyzer and the planner contain no LLM calls — deterministic.
- Every generated artifact cites the spec clause it satisfies.
- The four pluggable interfaces are the only extension points. Do not widen, do not bypass.
- Default-mode code paths must work offline.
- Runtime boundary — files in, files out. The tool never spawns processes, never
  runs git, never manages external services, never calls the system under test.
-->

- <your first invariant>
- <your second invariant>
