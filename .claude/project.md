# Project configuration

The single source of stack-specific facts. Every agent and workflow phase reads
its commands and patterns from here instead of hardcoding a toolchain, so the
same workflow drives any language. `/init-project` fills this in on first run.

Resolve a `${VARIABLE}` referenced anywhere in `.claude/` by looking it up in
the table below.

## Identity

| Variable | Value |
|---|---|
| `${PROJECT_NAME}` | agentic-scaffolding |
| `${TAGLINE}` | spec-first multi-agent TDD workflow template for Claude Code |
| `${LANGUAGE}` | Python (3.12+, stdlib only) |
| `${UNIT}` | module |
| `${MODULE_PREFIX}` | none |
| `${MAIN_BRANCH}` | main |

## Commands

Each is a complete shell command. `<unit>` is a literal placeholder a phase
substitutes with the target unit's path.

| Variable | Value | Notes |
|---|---|---|
| `${TEST_CMD}` | `python -m unittest discover -s tests -t .` | Must exit non-zero on any failure. |
| `${TEST_SCOPE_CMD}` | `python -m unittest discover -s tests -t . -k <unit>` | Scoped to the unit under work. |
| `${BUILD_CMD}` | `python -m compileall -q .` | Must exit non-zero on error. |
| `${LINT_CMD}` | none | Or "none" if the project has no linter. |
| `${FORMAT_CMD}` | none | Or "none". |

## Patterns

| Variable | Value |
|---|---|
| `${SOURCE_GLOB}` | `*.py` |
| `${TEST_GLOB}` | `tests/**/*.py` |
| `${EXPORT_PATTERN}` | `^def[[:space:]]` |
| `${NOT_IMPL}` | `raise NotImplementedError("not implemented")` |
| `${INTEGRATION_GATE}` | none — no integration tier; all tests are unit tests run by `${TEST_CMD}` |

## Dependencies and license

| Variable | Value |
|---|---|
| `${LICENSE}` | UNLICENSED (no license file yet) |
| `${LICENSE_ALLOWLIST}` | MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC |
| `${DEP_MANIFEST}` | requirements.txt |
| `${DEP_ADD_CMD}` | none |
| `${DEP_LICENSES_CMD}` | none |

## Notes

- `${NOT_IMPL}` is load-bearing: the failing-tests and implementation phases grep
  test output for the literal `not implemented`, which is how they stay
  language-agnostic. Keep that substring in whatever idiom you choose.
- If a command does not apply (no separate build step, no linter), set it to
  `none` and the phases will skip the corresponding gate.
- `scripts/check-licenses.sh` and `scripts/surface-drift.sh` (driver-run at PR
  review) parse `${DEP_MANIFEST}`, `${LICENSE_ALLOWLIST}`, `${DEP_LICENSES_CMD}`,
  `${SOURCE_GLOB}`, `${TEST_GLOB}`, and `${EXPORT_PATTERN}` straight from the
  tables above — keep those values literal (paths, globs, one command, one
  regex), never prose. Leading/trailing whitespace is trimmed, so anchor
  `${EXPORT_PATTERN}` with `[[:space:]]`, not a trailing space. Setting
  `${DEP_LICENSES_CMD}` or `${EXPORT_PATTERN}` to `none` makes the matching
  check report itself unavailable, which caps PR-review verdicts at comment.
- This repo is stdlib-only: `requirements.txt` does not exist and must stay
  absent — the license check then reports "dependencies unchanged". Tests use
  stdlib `unittest`; `tests/` is a package (`tests/__init__.py`).
- Value cells must never contain a `|` — the parsing scripts split rows on
  every pipe, quoted or not. Hence `${EXPORT_PATTERN}` matches only top-level
  `def` (no ERE alternation): public surface is functions; `class` lines do
  not register as surface drift.
