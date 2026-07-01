# Bootstrapping a new project from the workflow template

This guide takes you from an empty repo to a running spec-first TDD workflow driven by Claude Code. It assumes you have the template zip (`workflow-template.zip`).

The template is language-agnostic. Everything stack-specific is a `${...}` variable resolved from one file, `.claude/project.md`. You fill that in once, with `/init-project`, and the same eight-phase workflow then drives any language.

---

## 0. Prerequisites

- **git** and a repo host. The default workflow opens draft PRs with the **GitHub CLI (`gh`)** — install and `gh auth login`. (If you do not use GitHub, see "No GitHub" at the end.)
- **Claude Code** open in the repo.
- Your project's own toolchain installed — whatever runs your tests, build, linter, formatter. The workflow shells out to these, it does not install them.

---

## 1. Drop the template into an empty repo

```bash
mkdir my-project && cd my-project
git init
# unzip the template here — INCLUDE dotfiles (.claude/, .gitignore)
unzip /path/to/workflow-template.zip -d .
# the zip nests everything under workflow-template/ — flatten if so:
#   mv workflow-template/* workflow-template/.* . 2>/dev/null; rmdir workflow-template
chmod +x scripts/*.sh
git add -A && git commit -m "chore: scaffold workflow template"
```

Confirm the dotfiles came across: you should see `.claude/` and `.gitignore`. The `.gitignore` already excludes `.claude/settings.local.json` and `.claude/worktrees/`.

Create the `main` branch and push it once (the workflow branches from `origin/main`):

```bash
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

---

## 2. Run `/init-project`

In Claude Code, run:

```
/init-project
```

It interviews you, fills every placeholder in `.claude/project.md` and the prose stubs, then **deletes itself and `SETUP.md`** so no template scaffolding survives. Have these answers ready:

| It asks | Example (Node/TypeScript) | Example (Python) |
|---|---|---|
| Project name + tagline | `Acme API — billing service` | same shape |
| Language / stack | `TypeScript (Node 20)` | `Python 3.12` |
| Unit word | `package` | `module` |
| Whole-suite test cmd | `npm test` | `pytest` |
| Single-unit test cmd | `npm test -- <unit>` | `pytest <unit>` |
| Build / typecheck cmd | `tsc --noEmit` | `none` |
| Lint cmd | `eslint .` | `ruff check` |
| Format cmd | `prettier --write` | `ruff format` |
| Source glob | `src/**/*.ts` | `src/**/*.py` |
| Test glob | `**/*.test.ts` | `**/test_*.py` |
| "not implemented" idiom | `throw new Error("not implemented")` | `raise NotImplementedError("not implemented")` |
| Integration gate | `tests tagged @integration; unit = npm test, integration = npm run test:int` | `marker @pytest.mark.integration; unit = pytest -m "not integration"` |
| License + allowlist | `MIT` / `MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, MPL-2.0` | same |
| Dependency manifest | `package.json` | `pyproject.toml` |
| Add-dependency cmd | `npm install <pkg>@<version>` | `uv add <pkg>==<version>` |

**The one rule that matters:** the "not implemented" idiom **must contain the literal text `not implemented`**. The failing-tests and implementation phases grep test output for that string — it is how the workflow stays language-agnostic. Keep the substring whatever idiom you pick.

Optional in the same interview (can be left blank and filled later):
- A one-paragraph architecture summary.
- Any load-bearing **invariants** every change must preserve.
- How the project builds test doubles / fakes for unit tests.

`/init-project` Step 3 offers to tighten the agents' tool permissions. **Skip it the first time** — leaving `Bash` broad is fine, and on some setups editing an agent file through Claude is blocked (see Caveat below).

After it finishes, review the populated files and commit:

```bash
git add -A && git commit -m "chore: initialize project config"
```

---

## 3. Set your invariants (do this early, it pays off)

Open `.claude/agents/conventions/invariants.md` and write the handful of rules every change must hold — the things a reviewer should block on. Keep each one checkable from a diff. Examples of the shape:

- "The pricing engine is pure — no I/O, no clock reads."
- "Public API responses never include internal IDs."
- "Default code path runs without network access."

This file is the **single authoritative source** — all four agents load it. Never copy an invariant into a role file. The `/retro` command actively checks for that drift. Background reasoning for each invariant goes in `docs/decisions.md`, not here.

---

## 4. Build your first feature

```
/new-feature user-signup
```

The session drives all eight phases itself, spawning worker agents. You have **three human touchpoints** — everything else is automatic and gated:

1. **Scope confirmation (before any spec).** It lists the units, surface, dependencies, and adjacent work the ask implies, and asks you to confirm or narrow. Narrow aggressively here — anything you drop is recorded in the spec's Out-of-scope so the receipt survives. This is where you stop scope creep.
2. **Spec approval (Phase 2).** A `spec-reviewer` agent audits the spec for testability, interface completeness, and scope. Once it approves, you confirm the spec captures your intent. **After this point the spec is immutable** — a later change is a new spec that supersedes it, never an edit.
3. **PR verdict + merge.** A `pr-reviewer` agent runs your full toolchain, diffs against main, and posts an approve / request-changes / comment verdict on a draft PR. The workflow ends at "ready to merge." **You merge** — agents never do.

The phases in between are mechanical and strictly ordered:

```
spec → spec review → interface skeleton → failing tests (RED)
     → add deps → implementation (GREEN) → PR review → mark ready
```

Why this produces honest code: the `test-writer` writes failing tests against the interface *before* any implementation exists and cannot edit the implementation. The `implementer` makes them pass and cannot edit the tests. Different agents, hard file boundaries. Tests are not retrofitted to whatever the code happens to do.

If something interrupts the run, resume with:

```
/resume-feature user-signup
```

It detects the current phase from git history, shows you the evidence, and continues from there.

---

## 5. Non-feature work and parallelism

- **Chores** (refactors, docs, config, dependency bumps): `/new-chore <description>`. Runs in its own worktree on a `chore/<slug>` branch. No TDD state machine.
- **Parallel sessions** never share a working directory. Each feature and chore gets its own git worktree, so two sessions cannot clobber each other. Keep the main checkout clean on `main`.
- **After a branch merges:** run `./scripts/prune-worktrees.sh` from the main checkout. It removes only merged worktrees and branches, and skips anything dirty or unmerged.
- **New worktree missing permissions?** Run `./scripts/setup-worktree.sh` inside it to inherit the main checkout's approved permission grants, so agents are not re-prompted.

---

## 6. Keep the process healthy

After every handful of merges, run:

```
/retro
```

It scans recent git history for corrective signals — reverts, "drop/clarify/never" commits, specs edited after approval, invariant contradictions in changed docs, invariants duplicated outside the canonical file — and proposes **at most three small fixes**, applied as tiny commits on a `chore/retro-<date>` branch. It is bounded by design so it never becomes its own rabbit hole.

---

## 7. Caveat — editing agent definitions through Claude

On some setups, Claude's file tools refuse to create or edit files literally named `implementer.md`, `test-writer.md`, `spec-reviewer.md`, or `pr-reviewer.md` (a guard on agent-definition filenames). You will **not** hit this during normal bootstrapping — those four files ship pre-written and `/init-project` does not touch them (unless you opt into the Step 3 permission-tightening, which is why this guide says skip it).

If you later need to edit an agent definition and the tool refuses:
- Edit it in a normal text editor or the terminal, or
- Write the change to a differently-named staging file, then `mv` it into place.

This affects only agent-definition files. Everything else edits normally.

---

## 8. Customizing later

- **Commands, globs, license** — all in `.claude/project.md`. Change them there, never in the phase files.
- **Invariants** — `.claude/agents/conventions/invariants.md` only. Single source. Add, never duplicate.
- **Agent models** — each agent's frontmatter `model:` field. Defaults: `spec-reviewer` on a strong model, `implementer`/`test-writer` mid, `pr-reviewer` light.
- **No GitHub** — edit `phase-6.md`, `phase-7.md`, and `pr-reviewer.md` to review the local diff and stop at the branch instead of using `gh`. The rest of the workflow is unaffected.
- **Architecture docs** — `docs/architecture.md` is an index. As subsystems appear, add a page under `docs/architecture/` and a pointer line. Agents read the index plus only the one subsystem page their task touches, so keep pages focused.

---

## Quick reference

| Command | Use |
|---|---|
| `/init-project` | One-time setup. Interviews, fills placeholders, self-deletes. |
| `/new-feature <slug>` | Full 8-phase TDD workflow for a feature. |
| `/new-chore <desc>` | Isolated worktree for non-feature work. |
| `/resume-feature <slug>` | Resume an interrupted feature. |
| `/retro` | Bounded process retrospective, ≤3 fixes. |
| `./scripts/prune-worktrees.sh` | Remove merged worktrees and branches. |
| `./scripts/setup-worktree.sh` | Inherit permissions into a new worktree. |
