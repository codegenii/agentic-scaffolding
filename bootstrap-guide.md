# Bootstrapping a new project from this template

This guide covers **one-time setup** — getting from an empty or existing repo to a configured, running workflow. It ends at `/init-project`, and never leaves the template — the installer doesn't copy it. For everything after that — the phases, the agents, specs, invariants, parallel worktrees, adapting the workflow — read [CONTRIBUTING.md](CONTRIBUTING.md), which stays in your project.

The template is language-agnostic. Everything stack-specific is a `${...}` variable resolved from one file, `.claude/project.md`. `/init-project` fills it from a short interview, and the same eight-phase workflow then drives any language.

---

## Prerequisites

- **git** and a repo host. The default workflow opens draft PRs with the **GitHub CLI (`gh`)** — install and `gh auth login`. (Not using GitHub? See CONTRIBUTING.md → "Adapting the workflow".)
- **Claude Code** open in the repo.
- A local clone of this template.
- Your project's own toolchain installed — whatever runs your tests, build, linter, formatter. The workflow shells out to these, it does not install them.

---

## 1. Install the template

Clone this template once:

```bash
git clone <this-repo-url> template-clone
cd template-clone
```

**Empty repo** — create it, then install:

```bash
git init /path/to/target-repo
./scripts/install.sh /path/to/target-repo
```

**Existing repo** — install straight in:

```bash
./scripts/install.sh /path/to/target-repo
```

Core workflow files (`.claude/`, `scripts/`, …) are installed; existing project files (`README.md`, `CLAUDE.md`, docs) are left untouched and reported, and `.gitignore` only gains its two required lines if missing. The installed template commit is recorded in `.claude/template-version`, and re-running from a newer template clone is also how you update later: the run prints a pre-copy summary, refreshes core files you have not modified, and keeps locally modified ones unless you pass `--force`. See CONTRIBUTING.md → "Updating the workflow".

The installer never touches your git history. Commit the scaffold — for a brand-new repo, set up `main` and a remote first:

```bash
cd /path/to/target-repo
git branch -M main
git remote add origin <your-repo-url>
git add -A && git commit -m "chore: scaffold project"
git push -u origin main
```

---

## 2. Run `/init-project` — the last step

This is the final step of this guide, by design: `/init-project` interviews you, fills in the configuration, and on completion **self-destructs — removing its own setup scaffolding** so the finished project carries none of it. From here on your reference is `CONTRIBUTING.md`.

```bash
/init-project
```

**Existing codebase?** `/init-project` notices (a dependency manifest, a `src/` tree, or prior history) and runs in adopt mode: it infers most of the answers below from manifests, CI config, the file tree, and your `LICENSE`, shows one prefilled table to confirm, merges its sections into your existing `README.md`/`CLAUDE.md`/docs instead of replacing them, and runs your test and build commands once to report the baseline — red is reported, not fixed.

Have these answers ready:

| It asks | Example (Node/TypeScript) | Example (Python) |
| --- | --- | --- |
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

You're configured — `CONTRIBUTING.md` is your reference from here. Two things to do first:

- **Set your invariants.** Flesh out `.claude/agents/conventions/invariants.md` with the rules every change must hold. Doing this before your first feature pays off — reviewers enforce them from then on. (CONTRIBUTING.md → "Invariants".)
- **Build.** Run `/new-feature <slug>`. CONTRIBUTING.md walks the eight phases, the agents, and your three touchpoints — scope, spec approval, and merge.
