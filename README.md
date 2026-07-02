# ${PROJECT_NAME}

> ${TAGLINE}

<!-- init-project fills the name, tagline, and this overview from your answers. -->
<one-paragraph overview of what this project does>

## Development

This repo uses a spec-first, multi-agent TDD workflow driven by Claude Code. The stack-specific commands (test, build, lint, format) and file patterns live in `.claude/project.md`. The working agreement is in `CLAUDE.md`. New here? Start with [CONTRIBUTING.md](CONTRIBUTING.md) — it explains the workflow end to end.

Common commands:

- `/new-feature <slug>` — spec → failing tests → implementation → PR review.
- `/new-chore <description>` — isolated worktree for refactors, docs, config.
- `/resume-feature <slug>` — resume an interrupted feature.
- `/retro` — periodic process retrospective.

Specs live in `docs/specs/` and are immutable once approved — a change is a new spec that supersedes the old one, never an edit. See `docs/architecture.md` for the design and `docs/decisions.md` for the reasoning behind key choices.
