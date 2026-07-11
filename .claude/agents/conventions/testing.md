# Testing conventions (test-writer)

## Language

American English in test names, comments, helper names — word choice and spelling (behavior not behaviour, initialize not initialise).

## Commit messages

- `test(<unit>): <imperative>` — subject only, ≤ 50 chars, no period.

## Test structure

- Table/parameterized-driven in the language's idiom: one case per scenario.
- Case names are full sentences describing the scenario. Not `case1`, `case2`.
- One behavior per case. Split happy path, edge cases, and error conditions.
- Each spec behavior rule maps to at least one dedicated case. The mapping is traceable by the case name — never by referencing rule numbers (they drift).
- Group related cases under named subgroups so verbose test output is self-describing.
- Use the language's standard structural-equality / diff helper for comparing composite values.
- Mark shared assertion helpers as helpers in the language's idiom. Keep them file-private.

## Meaningful coverage

Every test must verify behavior that could actually fail for a reason worth catching — never something the compiler or language runtime already guarantees. Before writing a case, ask: is there a plausible code change that would make this assertion fail? If the only way to fail is "the language stopped working," don't write it. Coverage means exercising a symbol's real behavior — happy path, edge cases, declared errors — not a fixed quota of cases per symbol; a trivial one-line constructor or property getter needs exactly the case(s) that verify its one piece of behavior, nothing padded on top.

## Errors

- Compare errors by identity/type, never by matching message strings.

## External services

- Unit tests use injected fakes. Never real services or network.
- Integration tests sit behind `${INTEGRATION_GATE}` (see `.claude/project.md`) and run only when the spec's Test strategy authorizes them.

## File ownership

You write test files only (matching `${TEST_GLOB}`). Never non-test source, dependency manifests, or specs.

## Comments

Every comment must be true in every phase — red and green. Comment what the test permanently verifies. Never `"expected to fail"`, `"not yet implemented"`, `"currently fails on stub"`.
