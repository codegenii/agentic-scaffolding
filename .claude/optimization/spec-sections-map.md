# Spec-section extraction map

Which spec sections each phase extracts verbatim and passes inline to its agent. This keeps briefs small — the agent gets exactly the sections it needs, not the whole spec. Extraction is mechanical (see `.claude/orchestrator.md` "Spec section extraction"): copy every line under `## <Section>` up to the next `## `, never paraphrase.

| Phase | Agent | Sections passed |
|---|---|---|
| Phase 3 — Interface skeleton | implementer | `Interface contract`, `Behavior` |
| Phase 4 — Failing tests | test-writer | `Interface contract`, `Behavior`, `Test strategy` |
| Phase 5 — Implementation | implementer | `Interface contract`, `Behavior` |
| Phase 6 — PR review | pr-reviewer | `Purpose`, `Interface contract`, `Behavior`, `Out of scope`, `External dependencies` |

**spec-reviewer is exempt** — Phase 2 passes the spec path and the reviewer reads the full file. Every other agent works from extracted sections and must not read the spec file from disk (the path is for citation only).
