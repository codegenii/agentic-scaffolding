---
argument-hint: (none)
description: One-time setup — interview the operator and populate this template for a new or existing project
---

You are running the **one-time initialization** of this workflow template into a concrete project. Your job: interview the user, fill in every placeholder, and then delete yourself so no template scaffolding survives. Run this once, in a normal session (not a worktree), right after installing the template — into a fresh repo or an existing codebase.

## Step 0 — Guard

Read `.claude/project.md`. If its placeholders are already filled (no `<...>` angle-bracket placeholders remain in the Identity table), this project is already initialized — stop and tell the user, do not re-run.

Confirm the repo is a git repository (`git rev-parse --git-dir`). If not, tell the user to run `git init` first and stop.

**Mode:** check for existing source — a dependency manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `*.csproj`, …), a `src/` tree, or git history beyond the scaffold commit. Any of these means an existing codebase: run in **adopt mode** (next section). None means a fresh repo: the interview flow below runs unchanged. State the mode before proceeding.

## Adopt mode — existing codebase

Detect before asking. Items 1–2 replace Step 1, item 3 governs Step 2's writes, items 4–5 run after Step 2; Steps 3–5 are unchanged.

1. **Detect:** infer `${LANGUAGE}`, `${UNIT}`, and `${MODULE_PREFIX}` from the manifest(s); test/build/lint/format commands from manifest scripts, `Makefile`/`justfile`, and CI workflow files; `${SOURCE_GLOB}`/`${TEST_GLOB}` from the actual tree; `${LICENSE}` from an existing `LICENSE` file; `${MAIN_BRANCH}` from git.
2. **Confirm:** present one prefilled `project.md` table for the user to confirm or correct. Interview only what detection cannot supply: `${UNIT}` wording, `${NOT_IMPL}`, `${EXPORT_PATTERN}`, `${INTEGRATION_GATE}`, and the license allowlist.
3. **Merge, never clobber:**
   - `README.md` — keep it; add a short "Development" section pointing at `CONTRIBUTING.md` and the commands.
   - `CLAUDE.md` — keep its content; append the template's "Working in parallel" and "The workflow" sections.
   - Existing architecture/decision docs — link them from the stubs (or `CLAUDE.md`), never replace them.
   - `LICENSE` — read it to fill `${LICENSE}`; never rewrite it.
   - If the repo had its own `CONTRIBUTING.md` before install (the installer skipped the template's), write the template's copy to `docs/agentic-workflow.md` — from the template clone; ask for its path — and link it from `CLAUDE.md`.
4. **Baseline:** once `project.md` is confirmed, run `${TEST_CMD}` and `${BUILD_CMD}` once. Report a red baseline plainly and note that the phase gates assume a green `${MAIN_BRANCH}` — do not attempt fixes.
5. **Seed invariants:** mine existing conventions/style/architecture docs for candidate invariants for `.claude/agents/conventions/invariants.md`, confirming each item with the user.

## Step 1 — Interview

Ask the user for the following, in one batch where possible. Accept "none" for any command that does not apply.

### Identity

- Project name and a one-line tagline.
- Language / stack.
- The word for a unit of work in this stack: `package`, `module`, `crate`, `directory`, …
- Module/import path prefix, if any.

### Commands (exact shell commands)

- Whole-suite test command.
- Single-unit test command (how to scope tests to one `<unit>`).
- Build / typecheck command (or none).
- Lint command (or none).
- Format command (or none).

### Patterns

- Source file glob.
- Test file glob.
- The skeleton "not implemented" idiom for this language — it must contain the literal text `not implemented`.
- A POSIX extended regex matching a line that declares an exported/public symbol (used by `scripts/surface-drift.sh`), e.g. `^export[[:space:]]` for TypeScript — or none.
- How integration tests are separated from unit tests (a directory, a tag/marker, an env flag), with the command to run unit-only and integration-only.

### Dependencies and license

- License — **default `MIT`**. State the default and let the user override. If MIT, also ask for the copyright holder (default: the repo's git `user.name`).
- Allowed dependency licenses (allowlist) — **default `MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, MPL-2.0`**.
- Dependency manifest file(s) — literal space-separated paths.
- Command to add a pinned dependency.
- Command printing one `name version license` line per direct dependency (used by `scripts/check-licenses.sh`) — shape a license tool's output with a pipe — or none.

### Project specifics (optional, can be filled later)

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
6. `docs/architecture.md` and `docs/decisions.md` — replace the stub headers with the project's real summary (or leave as a stub the first feature will grow). Seed `docs/configuration.md`'s Quick start with how this stack supplies local secrets (its local-secret store, a gitignored `.env`, …) — the reference table grows as features add config keys.
7. `LICENSE` — create it for the chosen license. For MIT (the default), write the standard MIT text with the current year and the copyright holder. For any other license, insert that license's standard text verbatim, or a clearly-marked placeholder if you cannot reproduce it, and tell the user to paste the official text.

Leave `${...}` variable *references* inside the `.claude/` files as they are — they are resolved at read time from `project.md`, not substituted now. You are filling in `project.md`'s **values** and the prose stubs, not rewriting every reference.

## Step 3 — Optional: tighten agent tool permissions

The agent definitions other than `spec-writer` grant `Bash` broadly. If the user wants tighter permissions, narrow the `tools:` list in `implementer.md`, `test-writer.md`, and `pr-reviewer.md` to the specific commands from `project.md` (e.g. `Bash(npm test:*)`). Otherwise leave `Bash` as-is. Ask once; default to leaving it.

## Step 4 — Verify the workflow is runnable

- `scripts/*.sh` are present and executable (`chmod +x scripts/*.sh` if needed).
- For the PR flow, `gh auth status` is authenticated. If not, tell the user to authenticate before their first `/new-feature`.
- `.gitignore` ignores `.claude/settings.local.json` and `.claude/worktrees/`.

## Step 5 — Self-destruct

Once `project.md` has no remaining `<...>` placeholders:

1. Delete this command file: `rm .claude/commands/init-project.md`.
2. Remove template-development files if they rode along in the copy: `rm -f bootstrap-guide.md backlog.md`. They document the template itself and do not belong in a project built from it.
3. Report what was filled in, and tell the user the project is ready: run `/new-feature <slug>` to start the first feature, or `/new-chore <desc>` for non-feature work.

Do not commit — leave the populated files in the working tree for the user to review and commit themselves.
