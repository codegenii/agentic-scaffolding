# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## What this is

<!-- /init-project fills this in. One paragraph: what the project does and why. -->
`${PROJECT_NAME}` — `${TAGLINE}`.

The stack-specific facts — language, build/test/lint commands, file patterns, license — live in `.claude/project.md`. Every agent and workflow phase resolves its `${...}` variables from there.

See `docs/architecture.md` for the system design and `docs/decisions.md` for key technical choices and their reasoning.

## Working in parallel

Multiple Claude sessions may run against this repo at once — feature workflows and chores alike. They must not share a working directory, or one session's `git checkout` clobbers another's edits.

- The shared checkout (repo root, on `main`) is the **integration tree**. Keep it clean on `main` — never do task work directly in it.
- Every unit of work runs in its own git worktree on its own branch. Features: `/new-feature` and `/resume-feature` enter an isolated worktree and drive the feature workflow. Chores: `/new-chore` cuts the worktree and `chore/<slug>` branch for you.
- Branch naming: `feature/<slug>` for features, `chore/<slug>` for chores.
- Cleanup: once a branch is merged into `main`, run `./scripts/prune-worktrees.sh` from the main checkout to remove its worktree and delete the merged branch. It removes only merged branches and skips anything dirty or unmerged.
- Permissions: a worktree created by a plain `git worktree add` lacks the main checkout's `.claude/settings.local.json`. Run `./scripts/setup-worktree.sh` from inside the new worktree to copy or merge those local permission grants.
- File paths in worktrees: build Read/Edit/Write paths from the worktree root (`./` or `$PWD`), never from the main checkout's absolute path — those bypass the worktree and edit `main` by accident.
- Process health: run `/retro` after every handful of merges to catch corrective patterns early and apply small fixes before they compound.

## The workflow

Features follow a strict 8-phase TDD state machine driven by `.claude/orchestrator.md`: spec → spec review → add dependencies → interface skeleton → failing tests (red) → implementation (green) → PR review → mark ready. Specs are immutable once approved — a change is a new dated spec that supersedes the old one, never an edit. Four worker agents do the work under file-ownership boundaries: `spec-reviewer`, `implementer` (non-test source), `test-writer` (test files), `pr-reviewer`.

## Key design rules to preserve

- **Project-specific invariants** are the single authoritative list in `.claude/agents/conventions/invariants.md`. Every agent loads it. Add to it there, never duplicate it into a role file.
- **Specs are immutable once approved** — supersede, never edit (editorial fixes excepted). See `docs/specs/README.md`.
- **Merging is a human decision** — agents never merge PRs or branches. The workflow ends at "ready to merge".
- <!-- Add your own load-bearing rules here, or keep them only in invariants.md. -->

## CLI / commands

<!-- /init-project: list the project's own CLI commands or entry points here, if any. -->
