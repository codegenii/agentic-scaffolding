# Coding conventions (implementer)

Always-applicable rules for non-test source. They complement `${FORMAT_CMD}` and `${LINT_CMD}` (`.claude/project.md`) — they do not restate what those tools enforce.

## Language

All prose — comments, doc strings — uses American English spelling (behavior, color, canceled).

## Formatting and tooling

- `${FORMAT_CMD}`, `${LINT_CMD}`, and `${BUILD_CMD}` must be clean before any commit (skip any set to `none`).
- Follow the language's standard import/module ordering.

## Naming

- Names describe roles, in the language's idiom. No Hungarian notation or `I`-prefixed interfaces unless the language community expects them.
- Constructors and factories follow the language's standard naming.

## Doc comments

- Only where the WHY is non-obvious — a hidden constraint, invariant, or surprising choice. Trivial members (getters, assign-only constructors, one-line delegators) get none. A comment restating the name or signature is worse than none — omit it.
- Implementing a documented interface member: use the language's inherit-doc idiom (e.g. `/// <inheritdoc />`) instead of restating; if the language has none, omit.
- Never reference spec rule numbers — they drift. Name the behavior.

## Errors

- Wrap errors with context as the language idiom allows, preserving the original for typed comparison.
- Compare errors by identity/type, never by message strings.
- Distinct failure modes get distinct named errors.

## Configuration and secrets

- Never commit a real environment value — connection string, API key, password, token — into a tracked config file, even a development-only one. Leave the key absent or empty; supply the value via the language's local-secret store, an env var, or a gitignored local file, and note how near where it is read.
- Exception: a value provably never used to connect to anything real (e.g. a dummy connection string that design-time tooling only parses) — say so in its doc comment.
- `docs/configuration.md` is the canonical guide to every config key. Update it in the same change that adds, renames, or removes one.

## Warning suppressions

- No compiler/linter suppressions in hand-written code — fix the root cause. If genuinely unavoidable, justify it in an adjacent comment.
- Auto-generated files (e.g. ORM migration snapshots) are exempt — never hand-edit them.
