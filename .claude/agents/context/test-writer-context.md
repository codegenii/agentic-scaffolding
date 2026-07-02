# Test-writer architecture context

Read `.claude/project.md` for the language, test command, and integration gate. Conventions and the project invariants are in `.claude/agents/conventions/testing.md` and `.claude/agents/conventions/invariants.md` — both already loaded per your agent definition step 1.

## Fakes

<!-- /init-project seeds this. Describe how the project constructs test doubles
for its pluggable interfaces or external dependencies — where the fakes live,
the idiom for injecting them, and any shared test helpers. The test-writer uses
these for unit tests so they never touch real services. -->

<how this project fakes external dependencies for unit tests>

## Integration tests

Integration-classified tests are gated per `${INTEGRATION_GATE}`. Place them there and never let the unit suite call real services.
