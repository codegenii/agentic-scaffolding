# Bootstrapping a new project from this template

This guide covers **one-time setup** — getting from an empty repo to a configured, running workflow. It ends at `/init-project`, which is where it removes itself. For everything after that — the phases, the agents, specs, invariants, parallel worktrees, adapting the workflow — read [CONTRIBUTING.md](CONTRIBUTING.md), which stays in your project.

The template is language-agnostic. Everything stack-specific is a `${...}` variable resolved from one file, `.claude/project.md`. `/init-project` fills it from a short interview, and the same eight-phase workflow then drives any language.

---

## Prerequisites

- **git** and a repo host. The default workflow opens draft PRs with the **GitHub CLI (`gh`)** — install and `gh auth login`. (Not using GitHub? See CONTRIBUTING.md → "Adapting the workflow".)
- **Claude Code** open in the repo.
- Your project's own toolchain installed — whatever runs your tests, build, linter, formatter. The workflow shells out to these, it does not install them.

---

## 1. Copy the template into an empty repo

This repo *is* the template — bootstrapping means copying its files into a fresh repo, minus this repo's git history and this guide. From a local clone:

```bash
git clone --depth 1 <this-repo-url> my-project
cd my-project
rm -rf .git bootstrap-guide.md      # drop the template's history and this setup guide
git init
chmod +x scripts/*.sh
```

On a git host you can instead use **"Use this template"** (or fork). Either way you should end up with `.claude/`, `docs/`, `scripts/`, `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, and `.gitignore` at the repo root. If `bootstrap-guide.md` rode along in the copy, don't worry about it — `/init-project` removes it as part of its self-destruct.

The bundled `.gitignore` already excludes `.claude/settings.local.json` and `.claude/worktrees/`. Set up `main` and commit the scaffold:

```bash
git branch -M main
git remote add origin <your-repo-url>
git add -A && git commit -m "chore: scaffold project"
git push -u origin main
```

---

## 2. Run `/init-project` — the last step

This is the final step of this guide, by design: `/init-project` interviews you, fills in the configuration, and on completion **self-destructs — removing itself and this guide** so the finished project carries no setup scaffolding. From here on your reference is `CONTRIBUTING.md`.

```
/init-project
```

Have these answers ready:

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
| License (default `MIT`) + allowlist | `MIT` / `MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, MPL-2.0` | same |
| Dependency manifest | `package.json` | `pyproject.toml` |
| Add-dependency cmd | `npm install <pkg>@<version>` | `uv add <pkg>==<version>` |

**The one rule that matters:** the "not implemented" idiom **must contain the literal text `not implemented`**. The failing-tests and implementation phases grep test output for that string — it is how the workflow stays language-agnostic. Keep the substring whatever idiom you pick.

Optional in the same interview (leave blank and fill later if you prefer): a one-paragraph architecture summary, any load-bearing invariants, and how the project builds test doubles / fakes.

`/init-project` also offers to tighten the agents' tool permissions. **Skip that the first time** — leaving `Bash` broad is fine, and on some setups editing an agent file through Claude is blocked (see CONTRIBUTING.md → "Adapting the workflow").

When it finishes, review the populated files and commit:

```bash
git add -A && git commit -m "chore: initialize project config"
```

---

## What's next

You're configured, and this guide is gone — `CONTRIBUTING.md` is your reference from here. Two things to do first:

- **Set your invariants.** Flesh out `.claude/agents/conventions/invariants.md` with the rules every change must hold. Doing this before your first feature pays off — reviewers enforce them from then on. (CONTRIBUTING.md → "Invariants".)
- **Build.** Run `/new-feature <slug>`. CONTRIBUTING.md walks the eight phases, the agents, and your three touchpoints — scope, spec approval, and merge.
