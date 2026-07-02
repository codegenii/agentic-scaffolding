---
argument-hint: (none)
description: One-time setup — interview the operator and populate this template for a new project
---

You are running the **one-time initialization** of this workflow template into a concrete project. Your job: interview the user, fill in every placeholder, and then delete yourself so no template scaffolding survives. Run this once, in a normal session (not a worktree), right after copying the template into a fresh repo.

## Step 0 — Guard

Read `.claude/project.md`. If its placeholders are already filled (no `<...>` angle-bracket placeholders remain in the Identity table), this project is already initialized — stop and tell the user, do not re-run.

Confirm the repo is a git repository (`git rev-parse --git-dir`). If not, tell the user to run `git init` first and stop.

## Step 1 — Interview

Ask the user for the following, in one batch where possible. Accept "none" for any command that does not apply.

**Identity**
- Project name and a one-line tagline.
- Language / stack.
- The word for a unit of work in this stack: `package`, `module`, `crate`, `directory`, …
- Module/import path prefix, if any.

**Commands** (exact shell commands)
- Whole-suite test command.
- Single-unit test command (how to scope tests to one `<unit>`).
- Build / typecheck command (or none).
- Lint command (or none).
- Format command (or none).

**Patterns**
- Source file glob.
- Test file glob.
- The skeleton "not implemented" idiom for this language — it must contain the literal text `not implemented`.
- How integration tests are separated from unit tests (a directory, a tag/marker, an env flag), with the command to run unit-only and integration-only.

**Dependencies and license**
- License.
- Allowed dependency licenses (allowlist).
- Dependency manifest file(s).
- Command to add a pinned dependency.

**Project specifics** (optional, can be filled later)
- A one-paragraph architecture summary (subsystems, main extension points).
- Any load-bearing invariants every change must preserve.
- How the project constructs test doubles / fakes for unit tests.

## Step 2 — Populate the template

Write the answers into these files, replacing every placeholder:

1. `.claude/project.md` — the Identity, Commands, Patterns, and Dependencies tables. This is the hub every other file resolves `${...}` variables against.
2. `.claude/agents/conventions/invariants.md` — the invariants the user gave (or leave the template note if none yet).
3. `.claude/agents/context/implementer-context.md` and `test-writer-context.md` — the architecture paragraph and the fakes description.
4. `CLAUDE.md` — project name, tagline, and the "What this is" section.
5. `README.md` — project name, tagline, and overview. This file is human- and GitHub-facing, so substitute the real values, not `${...}` tokens.
6. `docs/architecture.md` and `docs/decisions.md` — replace the stub headers with the project's real summary (or leave as a stub the first feature will grow).

Leave `${...}` variable *references* inside the `.claude/` files as they are — they are resolved at read time from `project.md`, not substituted now. You are filling in `project.md`'s **values** and the prose stubs, not rewriting every reference.

## Step 3 — Optional: tighten agent tool permissions

The four agent definitions grant `Bash` broadly. If the user wants tighter permissions, narrow the `tools:` list in `implementer.md`, `test-writer.md`, and `pr-reviewer.md` to the specific commands from `project.md` (e.g. `Bash(npm test:*)`). Otherwise leave `Bash` as-is. Ask once; default to leaving it.

## Step 4 — Verify the workflow is runnable

- `scripts/*.sh` are present and executable (`chmod +x scripts/*.sh` if needed).
- For the PR flow, `gh auth status` is authenticated. If not, tell the user to authenticate before their first `/new-feature`.
- `.gitignore` ignores `.claude/settings.local.json` and `.claude/worktrees/`.

## Step 5 — Self-destruct

Once `project.md` has no remaining `<...>` placeholders:

1. Delete this command file: `rm .claude/commands/init-project.md`.
2. Remove the template's setup guide if it rode along in the copy: `rm -f bootstrap-guide.md`. It documents bootstrapping *from* the template and does not belong in a project built *from* it.
3. Report what was filled in, and tell the user the project is ready: run `/new-feature <slug>` to start the first feature, or `/new-chore <desc>` for non-feature work.

Do not commit — leave the populated files in the working tree for the user to review and commit themselves.
