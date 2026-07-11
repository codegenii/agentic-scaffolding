# Testing conventions (test-writer)

## Language

American English spelling in test names, comments, helper names (behavior not behaviour, initialize not initialise).

## Test structure

- Table/parameterized-driven in the language's idiom: one case per scenario.
- Case names are full sentences describing the scenario. Not `case1`, `case2`.
- One behavior per case. Split happy path, edge cases, and error conditions.
- Each spec behavior rule maps to at least one dedicated case, traceable by the case name — never by rule number (they drift).
- Group related cases under named subgroups so verbose output is self-describing.
- Use the language's standard structural-equality / diff helper for composite values.
- Mark shared assertion helpers as helpers in the language's idiom; keep them file-private.

## Meaningful coverage

Every case must verify behavior that could plausibly fail — never what the compiler or runtime already guarantees. Before writing one, ask: what code change would make this assertion fail? If the answer is "the language stopped working," skip it. Coverage means exercising a symbol's real behavior — happy path, edge cases, declared errors — not a per-symbol quota; a one-line getter needs exactly the case(s) for its one behavior.

## Errors

Compare errors by identity/type, never by message strings.

## External services

- Unit tests use injected fakes. Never real services or network.
- Integration tests sit behind `${INTEGRATION_GATE}` (see `.claude/project.md`) and run only when the spec's Test strategy authorizes them.

## Comments

Every comment must be true in every phase — red and green. Comment what the test permanently verifies. Never `"expected to fail"`, `"not yet implemented"`, `"currently fails on stub"`.
