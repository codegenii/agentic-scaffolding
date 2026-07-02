# Project configuration

The single source of stack-specific facts. Every agent and workflow phase reads
its commands and patterns from here instead of hardcoding a toolchain, so the
same workflow drives any language. `/init-project` fills this in on first run.

Resolve a `${VARIABLE}` referenced anywhere in `.claude/` by looking it up in
the table below.

## Identity

| Variable | Value |
|---|---|
| `${PROJECT_NAME}` | <PROJECT NAME> |
| `${TAGLINE}` | <one line: what this project is> |
| `${LANGUAGE}` | <e.g. TypeScript, Python, Rust, Go> |
| `${UNIT}` | <the unit of code a feature targets — "package", "module", "crate", "directory"> |
| `${MODULE_PREFIX}` | <import/module path prefix, or "none"> |

## Commands

Each is a complete shell command. `<unit>` is a literal placeholder a phase
substitutes with the target unit's path.

| Variable | Value | Notes |
|---|---|---|
| `${TEST_CMD}` | <run the whole test suite, e.g. `npm test`> | Must exit non-zero on any failure. |
| `${TEST_SCOPE_CMD}` | <run tests for one unit, e.g. `npm test -- <unit>`> | Scoped to the unit under work. |
| `${BUILD_CMD}` | <compile/typecheck, e.g. `npm run build` / `tsc --noEmit`> | Must exit non-zero on error. |
| `${LINT_CMD}` | <lint, e.g. `eslint .`> | Or "none" if the project has no linter. |
| `${FORMAT_CMD}` | <format check/apply, e.g. `prettier --write`> | Or "none". |

## Patterns

| Variable | Value |
|---|---|
| `${SOURCE_GLOB}` | <source files, e.g. `src/**/*.ts` excluding tests> |
| `${TEST_GLOB}` | <test files, e.g. `**/*.test.ts`> |
| `${NOT_IMPL}` | <skeleton stub idiom — MUST contain the literal text `not implemented`, e.g. `throw new Error("not implemented")`, `raise NotImplementedError("not implemented")`, `todo!("not implemented")`> |
| `${INTEGRATION_GATE}` | <how integration tests are separated from unit tests — a test directory, a tag/marker, an env flag. State how to run unit-only and how to run integration-only.> |

## Dependencies and license

| Variable | Value |
|---|---|
| `${LICENSE}` | <project license, e.g. MIT> |
| `${LICENSE_ALLOWLIST}` | <allowed dependency licenses, e.g. MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, MPL-2.0> |
| `${DEP_MANIFEST}` | <dependency manifest file(s), e.g. `package.json` + lockfile> |
| `${DEP_ADD_CMD}` | <add a pinned dependency, e.g. `npm install <pkg>@<version>`> |

## Notes

- `${NOT_IMPL}` is load-bearing: the failing-tests and implementation phases grep
  test output for the literal `not implemented`, which is how they stay
  language-agnostic. Keep that substring in whatever idiom you choose.
- If a command does not apply (no separate build step, no linter), set it to
  `none` and the phases will skip the corresponding gate.
