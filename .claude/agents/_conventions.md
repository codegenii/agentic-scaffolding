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

American English in all prose — word choice and spelling (favorite not favourite, behavior not behaviour, color, organize, canceled, license). Docs are terse — state the rule, do not restate referenced files.

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

In code, a doc comment appears only where the WHY is non-obvious — a hidden constraint, invariant, or surprising choice. A comment that merely restates the symbol's name or signature is a defect: flag restatement, not omission. Implementations of documented interface members use the language's inherit-doc idiom instead of restating. (Specs are different: the Interface contract documents every symbol — that is the contract, not code style.)

### Configuration and secrets

A real secret — connection string, API key, password, token — in any tracked file is blocking, even a development-only one. A change that adds, renames, or removes a config key without updating `docs/configuration.md` is blocking.

### Warning suppressions

A new compiler/linter suppression in hand-written code without an adjacent comment justifying it is blocking. Auto-generated files are exempt.

### License (allowlist)

This project is `${LICENSE}`. Allowed dependency licenses: `${LICENSE_ALLOWLIST}`. Anything else (GPL/LGPL/AGPL/SSPL/BUSL/CC-BY-SA and other copyleft or source-available) is forbidden. Detail in `_conventions-reference.md`.
