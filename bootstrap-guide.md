# Bootstrapping a new project from this template

This guide takes you from an empty repo to a configured, running workflow. It covers **one-time setup only** — for how development works day to day (the phases, the agents, specs, parallel worktrees), see [CONTRIBUTING.md](CONTRIBUTING.md).

The template is language-agnostic. Everything stack-specific is a `${...}` variable resolved from one file, `.claude/project.md`. You fill that in once, with `/init-project`, and the same eight-phase workflow then drives any language.

---

## 0. Prerequisites

- **git** and a repo host. The default workflow opens draft PRs with the **GitHub CLI (`gh`)** — install and `gh auth login`. (Not using GitHub? See "Adapting" at the end.)
- **Claude Code** open in the repo.
- Your project's own toolchain installed — whatever runs your tests, build, linter, formatter. The workflow shells out to these, it does not install them.

---

## 1. Unpack the template into an empty repo

The template ships as `workflow-template.zip` and unpacks **flat** — its contents (`.claude/`, `docs/`, `scripts/`, `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `.gitignore`) land at the repo root, no wrapper folder.

```bash
mkdir my-project && cd my-project
git init
unzip /path/to/workflow-template.zip -d .   # dotfiles included
chmod +x scripts/*.sh
```

Confirm the dotfiles arrived: you should see `.claude/` and `.gitignore` (which already excludes `.claude/settings.local.json` and `.claude/worktrees/`). Then set up `main` and commit the scaffold:

```bash
git branch -M main
git remote add origin <your-repo-url>
git add -A && git commit -m "chore: scaffold project"
git push -u origin main
```

---

## 2. Run `/init-project`

In Claude Code:

```
/init-project
```

It interviews you, fills every placeholder in `.claude/project.md`, `README.md`, `CLAUDE.md`, and the prose stubs, then **deletes itself** so no setup command lingers. Have these answers ready:

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
| Integration gate | `tag @integration; unit = npm test, integration = npm run test:int` | `marker @pytest.mark.integration; unit = pytest -m "not integration"` |
| License + allowlist | `MIT` / `MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, MPL-2.0` | same |
| Dependency manifest | `package.json` | `pyproject.toml` |
| Add-dependency cmd | `npm install <pkg>@<version>` | `uv add <pkg>==<version>` |

**The one rule that matters:** the "not implemented" idiom **must contain the literal text `not implemented`**. The failing-tests and implementation phases grep test output for that string — it is how the workflow stays language-agnostic. Keep the substring whatever idiom you pick.

Optional in the same interview (can be left blank and filled later): a one-paragraph architecture summary, any load-bearing invariants, and how the project builds test doubles / fakes.

`/init-project` Step 3 offers to tighten the agents' tool permissions. **Skip it the first time** — leaving `Bash` broad is fine, and on some setups editing an agent file through Claude is blocked (see Caveat below).

Review the populated files and commit:

```bash
git add -A && git commit -m "chore: initialize project config"
```

---

## 3. Set your invariants early

Open `.claude/agents/conventions/invariants.md` and write the handful of rules every change must hold — the things a reviewer should block on, each checkable from a diff. Examples of the shape:

- "The pricing engine is pure — no I/O, no clock reads."
- "Public API responses never include internal IDs."
- "Default code path runs without network access."

This file is the **single authoritative source** — all four agents load it, and `/retro` checks that no copy drifts into a role file. Reasoning behind each invariant goes in `docs/decisions.md`. (More on this in [CONTRIBUTING.md](CONTRIBUTING.md).)

---

## 4. Start building

You are now bootstrapped. Kick off the first feature:

```
/new-feature <slug>
```

It runs the full eight-phase TDD workflow, asking you to weigh in at three points — scope, spec approval, and merge — and driving everything else automatically. **[CONTRIBUTING.md](CONTRIBUTING.md) walks the phases, the agents, and those touchpoints in detail** — read it once and you know the whole flow. `/resume-feature <slug>` picks up an interrupted run, `/new-chore <desc>` handles non-feature work, `/retro` keeps the process healthy.

---

## Caveat — editing agent definitions through Claude

On some setups, Claude's file tools refuse to create or edit files literally named `implementer.md`, `test-writer.md`, `spec-reviewer.md`, or `pr-reviewer.md` (a guard on agent-definition filenames). You will **not** hit this during normal bootstrapping — those four files ship pre-written and `/init-project` does not touch them (which is why Step 3 above says skip the permission-tightening). If you later need to edit one and the tool refuses, edit it in a normal text editor or the terminal, or write to a differently-named staging file and `mv` it into place. Nothing else is affected.

---

## Adapting

- **No GitHub** — edit `.claude/orchestrator/phases/phase-6.md`, `phase-7.md`, and `.claude/agents/pr-reviewer.md` to review the local diff and stop at the branch instead of using `gh`. The rest of the workflow is unaffected.
- **Agent models** — set per agent in each definition's frontmatter `model:` field.
- Everything else stack-specific lives in `.claude/project.md`. Change it there, never in the phase files.
