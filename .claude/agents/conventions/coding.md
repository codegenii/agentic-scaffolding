# Coding conventions (implementer)

Always-applicable rules for non-test source. These complement the project's formatter and linter (`${FORMAT_CMD}`, `${LINT_CMD}` in `.claude/project.md`) — they do not restate what those tools already enforce.

## Language

All prose — comments, doc strings, commit messages — uses American English: word choice and spelling (favorite, behavior, color, organize, canceled). State the rule, do not restate referenced files.

## Commit messages

- Subject only. ≤ 50 chars, imperative, no trailing period.
- `type(scope):` prefix — `spec`, `feat`, `test`, `fix`, `chore`, `docs`.
- No body unless a load-bearing reason will not fit in the subject.
- Do not restate the branch name or slug in the subject — the scope already names it.

## Formatting and tooling

- `${FORMAT_CMD}` and `${LINT_CMD}` must be clean before any commit (skip whichever is `none`).
- `${BUILD_CMD}` must succeed before any commit (skip if `none`).
- Follow the language's standard import/module ordering.

## Naming

- Names describe roles, in the language's idiom. Avoid Hungarian notation and `I`-prefixed interface names unless the language community expects them.
- Error and failure values are distinct and named, not described only as "an error".
- Constructors and factories follow the language's standard naming.

## Doc comments

- Every exported symbol has a doc comment.
- It starts with the symbol name and explains the WHY, not the WHAT.
- No references to spec rule numbers — they drift. Name the behavior directly.

## Errors

- Wrap errors with context as the language idiom allows, preserving the original for typed comparison.
- Compare errors by identity/type, never by matching message strings.
- Distinct failure modes get distinct named errors.

## File ownership

You write non-test source files only. Never test files (matching `${TEST_GLOB}`), dependency manifests (`${DEP_MANIFEST}`), or specs.

**Editorial spec edits are exempt** — behavior-neutral edits (typo, rename, clarification) may be made directly to keep the spec in step with code. See `docs/specs/README.md`.

License allowlist for new dependencies: see `.claude/agents/_conventions-reference.md`.
