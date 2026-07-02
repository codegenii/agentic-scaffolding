# Contributing

This project uses a **spec-first, multi-agent TDD workflow** driven by Claude Code. This document explains how that flow works so you can pick it up quickly. Stack-specific commands (test, build, lint, format) live in `.claude/project.md`; the working agreement is in `CLAUDE.md`.

## Commands

| Command | Use |
|---|---|
| `/new-feature <slug>` | Full spec → tests → implementation → PR workflow for a new feature. |
| `/new-chore <description>` | Isolated worktree for non-feature work (refactors, docs, config, dependency bumps). |
| `/resume-feature <slug>` | Resume an interrupted feature — the phase is detected from git history. |
| `/retro` | Bounded process retrospective — proposes at most three small fixes. |

## The feature workflow

A feature runs through eight strictly-ordered phases, each with objective entry and exit gates and an iteration cap. Nothing is skipped or reordered.

```
spec → spec review → interface skeleton → failing tests (RED)
     → add deps → implementation (GREEN) → PR review → mark ready
```

The driving session sequences the phases and spawns worker agents — it never writes code itself. Four agents do the work, under hard file-ownership boundaries:

| Agent | Writes | Never touches |
|---|---|---|
| `spec-reviewer` | nothing (verdict only) | — |
| `implementer` | non-test source | test files, specs |
| `test-writer` | test files | non-test source, specs |
| `pr-reviewer` | the PR review (verdict) | code |

**Why this produces honest code:** the `test-writer` writes failing tests against the interface *before* any implementation exists and cannot edit the implementation. The `implementer` makes them pass and cannot edit the tests. Different agents, separate file ownership — so tests are not quietly reshaped to match whatever the code happens to do.

## Your three touchpoints

Most of the workflow is automatic and gated. You are asked to weigh in three times:

1. **Scope confirmation** — before any spec is written, you confirm or narrow what the feature covers. Narrow aggressively; anything dropped is recorded in the spec's Out-of-scope. This is where scope creep is stopped.
2. **Spec approval** — after `spec-reviewer` approves, you confirm the spec captures your intent. **From this point the spec is immutable.**
3. **Merge** — the workflow ends at "ready to merge" on a draft PR that passed review. **You merge.** Agents never merge or close PRs.

## Specs

Feature specs live in `docs/specs/` as `<date>-<slug>.md`, indexed by `docs/specs/README.md`. A spec's **behavior is immutable once approved** — changing what a feature does is a new dated spec that *supersedes* the old one, never an edit. Behavior-neutral edits (typos, renames, clarifications) are made in place.

## Invariants

The load-bearing rules every change must preserve live in **one** file: `.claude/agents/conventions/invariants.md`. All four agents load it. Add rules there — never copy an invariant into a role file (the `/retro` command checks for that drift). The reasoning behind each invariant belongs in `docs/decisions.md`.

## Working in parallel

Every unit of work runs in its own git worktree on its own branch, so parallel sessions never clobber each other. Keep the shared checkout clean on `main`.

- After a branch merges, run `./scripts/prune-worktrees.sh` from the main checkout — it removes only merged worktrees and branches.
- If a new worktree re-prompts for permissions, run `./scripts/setup-worktree.sh` inside it to inherit the main checkout's grants.
- Run `/retro` after every handful of merges to catch corrective patterns early.

## Where things live

| Path | What |
|---|---|
| `.claude/project.md` | Stack config — every `${...}` variable resolves here. |
| `.claude/orchestrator.md` + `orchestrator/phases/` | The eight-phase state machine. |
| `.claude/agents/` | The four worker agents, their conventions, and context cards. |
| `.claude/agents/conventions/invariants.md` | The single source of project invariants. |
| `docs/architecture.md` | Design index; subsystem detail under `docs/architecture/`. |
| `docs/decisions.md` | Why key choices were made (ADR-style). |
| `docs/specs/` | Feature specs and the registry. |
