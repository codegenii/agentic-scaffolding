# Conventions index

Loaded by spec-reviewer and pr-reviewer, alongside `conventions/invariants.md`. implementer loads `conventions/coding.md`, test-writer `conventions/testing.md`, and spec-writer `conventions/specs.md` instead — not this file.

The project-specific invariants live in `.claude/agents/conventions/invariants.md` — the single authoritative copy. The section below is a review-time style baseline, not that list.

## Always-applicable invariants (spec-reviewer + pr-reviewer)

These cross-cut prose and code and are enforced at review time.

### Language

American English in all prose — word choice and spelling (favorite not favourite, behavior not behaviour, color, organize, canceled, license). Docs are terse — state the rule, do not restate referenced files.

### File ownership

- `test-writer` writes test files (matching `${TEST_GLOB}`), nothing else.
- `implementer` writes non-test source, never test files.
- `spec-writer` writes the draft feature spec named in its brief, nothing else.
- The feature-workflow driver writes the spec registry.

**Editorial spec edits are exempt** — behavior-neutral edits may be made directly by any session. See `docs/specs/README.md`.

### Naming

- Names describe roles in the language's idiom. No Hungarian notation, no `I`-prefixed interfaces unless the language expects them.
- Error/failure values are distinct and named.
- Constructors and factories follow the language's standard naming.

### Doc comments

In code, doc comments appear only where the WHY is non-obvious. Flag restatement (a comment echoing the name or signature), not omission. Implementations of documented interface members inherit docs, never restate. Specs are exempt: the Interface contract documents every symbol.

### Configuration and secrets

A real secret — connection string, API key, password, token — in any tracked file is blocking, even a development-only one. A change that adds, renames, or removes a config key without updating `docs/configuration.md` is blocking.

### Warning suppressions

A new compiler/linter suppression in hand-written code without an adjacent comment justifying it is blocking. Auto-generated files are exempt.

### License (allowlist)

This project is `${LICENSE}`. Allowed dependency licenses: `${LICENSE_ALLOWLIST}`. Anything else (GPL/LGPL/AGPL/SSPL/BUSL/CC-BY-SA and other copyleft or source-available) is forbidden, transitive dependencies included; an unknown or ambiguous license is forbidden until verified.
