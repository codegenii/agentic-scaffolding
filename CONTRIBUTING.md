# Contributing

This project uses a **spec-first, multi-agent TDD workflow** driven by Claude Code. This document explains how that flow works so you can pick it up quickly. Stack-specific commands (test, build, lint, format) live in `.claude/project.md`; the working agreement is in `CLAUDE.md`.

## Commands

| Command | Use |
| --- | --- |
| `/new-feature <slug> [use haiku] <criteria>` | Full spec → tests → implementation → PR workflow for a new feature. |
| `/new-chore <description>` | Isolated worktree for non-feature work (refactors, docs, config, dependency bumps). |
| `/resume-feature <slug> [use haiku]` | Resume an interrupted feature — the phase is detected from git history. |
| `/retro` | Bounded process retrospective — proposes at most three small fixes. |

## Driver model

The session you type `/new-feature` into **is** the driver — there is no separate orchestrator process, because only the top-level session can spawn the worker agents. Two consequences:

- **The default is sonnet.** Driver intelligence is not the binding constraint — long-horizon guardrail persistence is. The driver holds the workflow's guardrails (worktree discipline, phase gates) across the longest transcript in the system, and instruction adherence decays with transcript depth, steeply on small models: haiku drivers drifted off core instructions by ~50% context usage, well before compaction.
- **The directive is an assertion, not a switch.** A command cannot change the model your session runs on; only you can, with `/model`. The directive declares which model the run expects, and the command verifies it *before touching anything* — on a mismatch it stops and names the exact `/model` command to run. The expectation is a floor: a session on a stronger model than requested passes.

Opt down with `use haiku` (or `--haiku`) for short, shallow-transcript runs only — besides the drift risk, haiku's 200K context risks mid-feature compaction, sonnet's 1M does not. Opt up with `use opus` (`--opus`). The choice is per run, not per feature: directives never persist across resumes, so a haiku-opted feature resumes on the default sonnet unless the directive is repeated.

Write the directive immediately after the slug, before the criteria, so it never gets lost in a long feature prompt:

```text
/new-feature rate-limiter Per-IP rate limiting on the public API.            ← sonnet (default)
/new-feature rate-limiter use haiku Per-IP rate limiting on the public API.  ← short run: haiku
/resume-feature rate-limiter                     ← resumes on sonnet (directives don't persist)
```

## The feature workflow

A feature runs through eight strictly-ordered phases, each with objective entry and exit gates and an iteration cap. Nothing is skipped or reordered.

```text
spec → spec review → add deps → interface skeleton
     → failing tests (RED) → implementation (GREEN) → PR review → mark ready
```

The driving session sequences the phases and spawns worker agents — it never writes code or spec drafts itself. Five agents do the work, under hard file-ownership boundaries:

| Agent | Writes | Never touches |
| --- | --- | --- |
| `spec-writer` | the feature spec draft | source, tests, the spec registry |
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

The load-bearing rules every change must preserve live in **one** file: `.claude/agents/conventions/invariants.md`. The feature driver pastes its list into every worker brief (`## Project invariants`); spec-reviewer and pr-reviewer load the file directly. Add rules there — never copy an invariant into a role file (the `/retro` command checks for that drift). The reasoning behind each invariant belongs in `docs/decisions.md`.

## Working in parallel

Every unit of work runs in its own git worktree on its own branch, so parallel sessions never clobber each other. Keep the shared checkout clean on `main`.

- After a branch merges, run `./scripts/prune-worktrees.sh` from the main checkout — it removes only merged worktrees and branches.
- If a hand-made worktree re-prompts for permissions, run `./scripts/setup-worktree.sh` inside it to inherit the main checkout's grants (the workflow commands do this automatically).
- Run `/retro` after every handful of merges to catch corrective patterns early.

## Where things live

| Path | What |
| --- | --- |
| `.claude/project.md` | Stack config — every `${...}` variable resolves here. |
| `.claude/orchestrator.md` + `orchestrator/phases/` | The eight-phase state machine. |
| `.claude/agents/` | The five worker agents, their conventions, and context cards. |
| `.claude/agents/conventions/invariants.md` | The single source of project invariants. |
| `docs/architecture.md` | Design index; subsystem detail under `docs/architecture/`. |
| `docs/configuration.md` | How to supply configuration locally — secrets are never committed. |
| `docs/decisions.md` | Why key choices were made (ADR-style). |
| `docs/specs/` | Feature specs and the registry. |

## Adapting the workflow

- **Commands, globs, license** — all in `.claude/project.md`. Change them there, never in the phase files.
- **Agent models** — set per agent in each definition's frontmatter `model:` field. The defaults are deliberate, validated over six real features:
  - `spec-writer` **opus** — drafting quality is the binding constraint; driver-drafted specs drew change requests on 4 of 6 features, and every revision round costs a full opus review.
  - `spec-reviewer` **opus** — one call per feature guarding the highest-leverage gate; cheap insurance.
  - `implementer`, `test-writer` **sonnet**.
  - `pr-reviewer` **haiku** — its inputs arrive pre-validated (green tests, clean build, driver-run license and surface-drift checks), so the checklist is mechanical.

  The driver is not one of these — it runs on your session's model, gated by the commands. See [Driver model](#driver-model).
- **No GitHub** — the default flow opens a draft PR with `gh`. To drop it, edit `.claude/orchestrator/phases/phase-7.md`, `phase-8.md`, and `.claude/agents/pr-reviewer.md` to review the local diff and stop at the branch. The rest of the workflow is unaffected.
- **Editing agent definitions** — on some setups Claude's file tools refuse to write files literally named `implementer.md`, `test-writer.md`, `spec-writer.md`, `spec-reviewer.md`, or `pr-reviewer.md`. If you hit it, edit the file in a normal text editor or the terminal, or write to a differently-named staging file and `mv` it into place. Nothing else is affected.

## Updating the workflow

The installer is also the updater. `.claude/template-version` records which template commit this repo carries.

1. Pull (or re-clone) the template checkout.
2. From it, run `./scripts/install.sh /path/to/this-repo`.
3. Review the pre-copy summary and the resulting `git diff`, then commit.

Core workflow files you have not touched are updated in place. A core file you modified locally is kept and reported — re-run with `--force` to overwrite it; either way, reconciling your modifications with the template's changes is this repo's job. Stub files (`README.md`, `CLAUDE.md`, this file, the docs, `.claude/project.md`, the invariants and agent context cards) never update automatically — port template improvements into them by hand if you want them.
