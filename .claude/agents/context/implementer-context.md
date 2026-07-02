# Implementer architecture context

Read `.claude/project.md` for the language, commands, and idioms. Work within the `${UNIT}` the brief names — read its existing files, do not range across the codebase.

## Architecture

<!-- /init-project seeds a one-paragraph summary here. Keep it short: the
subsystems and the extension points an implementer needs, not the full design.
Point to docs/architecture.md and its subsystem pages for detail. -->

`${PROJECT_NAME}` — <one-paragraph architecture summary: the main subsystems and how this unit fits>.

## Extension points

<!-- If the project has designated pluggable interfaces or seams that must not
be widened or bypassed, name them here. Otherwise delete this section. -->

The project's invariants are in `.claude/agents/conventions/invariants.md` — already loaded per your agent definition step 1.

Background reasoning, if needed: `docs/decisions.md`. Do not load it unless the brief asks.
