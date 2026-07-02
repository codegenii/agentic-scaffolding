# Conventions index

This file is the pointer index. Individual conventions files are loaded by the agents that need them — do not load the others.

| Agent | Files it loads |
|---|---|
| implementer | `.claude/project.md` + `conventions/coding.md` + `conventions/invariants.md` |
| test-writer | `.claude/project.md` + `conventions/testing.md` + `conventions/invariants.md` |
| spec-reviewer | this file (below) + `conventions/invariants.md` + `_conventions-reference.md` for the **Specs** section |
| pr-reviewer | this file (below) + `conventions/invariants.md` + `_conventions-reference.md` for the **License** allowlist |

The project-specific invariants every agent enforces live in `.claude/agents/conventions/invariants.md` — the single authoritative copy. The **Always-applicable invariants** section below is a separate, review-time style baseline, not that list.

## Always-applicable invariants (spec-reviewer + pr-reviewer)

These cross-cut prose and code and are enforced at review time.

### Language

One consistent natural-language locale in all prose. Docs are terse — state the rule, do not restate referenced files.

### File ownership

- `test-writer` writes test files (matching `${TEST_GLOB}`), nothing else.
- `implementer` writes non-test source, never test files.
- The feature-workflow driver writes specs and the spec registry.

**Editorial spec edits are exempt** — behavior-neutral edits may be made directly by any session. See `docs/specs/README.md`.

### Naming

- Names describe roles in the language's idiom. No Hungarian notation, no `I`-prefixed interfaces unless the language expects them.
- Error/failure values are distinct and named.
- Constructors and factories follow the language's standard naming.

### Doc comments

Every exported symbol has a doc comment, starting with the symbol name. Explain WHY.

### License (allowlist)

This project is `${LICENSE}`. Allowed dependency licenses: `${LICENSE_ALLOWLIST}`. Anything else (GPL/LGPL/AGPL/SSPL/BUSL/CC-BY-SA and other copyleft or source-available) is forbidden. Detail in `_conventions-reference.md`.
