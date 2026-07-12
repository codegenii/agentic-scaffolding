---
argument-hint: <slug> [use sonnet | use opus]
description: Resume an interrupted feature workflow
---

You are resuming an interrupted feature workflow. The raw argument is: `$ARGUMENTS`. The workflow runs in **this** session — there is no separate "orchestrator" agent to spawn.

## Step 0 — Driver model gate

Same gate as `/new-feature`: features are driven on **haiku** by default, with `use sonnet` (or `--sonnet`) and `use opus` (or `--opus`) as explicit opt-ups. The model is chosen per run, not locked at feature start — resuming on a bigger model than the one that started the feature is a normal move (a haiku-driven feature whose context grew too large resumes with `use sonnet`), and a feature started with `use sonnet` needs the directive again on resume. The canonical position is immediately after the slug — `/resume-feature rate-limiter use sonnet`.

1. Resolve the requested driver model from `$ARGUMENTS`: `sonnet` if it contains `use sonnet` or `--sonnet`, `opus` if it contains `use opus` or `--opus`, otherwise `haiku`.
2. Compare against the model this session runs on (your system prompt names it). Match by family — any Haiku model satisfies `haiku`, any Sonnet satisfies `sonnet`, any Opus satisfies `opus`.
3. On mismatch, stop before touching anything — you cannot switch the session model yourself — and tell the user:

   > "This run expects the driver on `<requested model>` (default haiku; opt up with `use sonnet` / `use opus`), but this session runs on `<session model>` — a command cannot switch the session's model. Run `/model <requested model>`, then re-run this exact `/resume-feature` command."

4. On match, ignore the model directive for the remaining steps and proceed.

## Step 1 — Validate the slug

Extract the slug from `$ARGUMENTS` (first whitespace-delimited token). A valid slug is lowercase kebab-case. If invalid, stop:

> "Invalid slug `<value>`. Must be lowercase kebab-case (e.g. `user-auth-refresh`)."

## Step 2 — Enter the feature's worktree

The branch `feature/<slug>` already exists from the interrupted run. Put this session in an isolated worktree on it:

1. Run `git fetch origin`. If neither a local `feature/<slug>` nor `origin/feature/<slug>` exists, stop:
   ```
   RESUME ERROR: branch feature/<slug> does not exist. Nothing to resume.
   ```
2. Locate the branch's checkout: run `git worktree list --porcelain` and look for a worktree that already has `feature/<slug>` checked out — the usual leftover when the interrupted session was abandoned rather than cleaned up (e.g. a haiku run whose context overloaded).
   - Found under `.claude/worktrees/` → reuse it: call `EnterWorktree` with that path and continue at step 3.
   - Found anywhere else → stop and tell the user to free that checkout first.
   - Not found → run `git worktree add .claude/worktrees/resume-<slug> feature/<slug>`, then call `EnterWorktree` with `path: .claude/worktrees/resume-<slug>`.

   This skill is the explicit instruction that authorizes `EnterWorktree`.
3. If `git status --porcelain` is non-empty, stop and report the uncommitted changes verbatim. Do not proceed until the working tree is clean.

## Step 3 — Detect the current phase

Run these and record all output:

1. `git log --stat main..HEAD` — commits on this branch since it diverged from main, with the files each one touched.
2. The test suite — full output and exit code. Derive the target `<unit>` from the file paths in the `git log --stat` output; if the branch's commits all point at one unit, run `${TEST_SCOPE_CMD}` scoped to it. If the derivation is ambiguous — paths spanning multiple units, or no recognizable unit — fall back to `${TEST_CMD}` (full suite).
3. `gh pr list --head feature/<slug> --json number,isDraft,state` — PR state.

Match the **most recent** commit's subject against the table below, top-to-bottom, stopping at the first row whose conditions all hold (most-advanced phase first):

| Most recent commit subject | tests | Open PR | Last completed phase | Resume from |
|---|---|---|---|---|
| `feat(...): implementation` or `fix(...): address review` | pass | open, not draft | Phase 7 — PR review | Phase 8 — Mark ready |
| `feat(...): implementation` or `fix(...): address review` | pass | open, draft | Phase 7 (in progress) | Phase 7 (continue) |
| `feat(...): implementation` or `fix(...): address review` | pass | none | Phase 6 — Implementation | Phase 7 — PR review |
| `test(...): failing suite` | fail, all `not implemented` | none | Phase 5 — Failing tests | Phase 6 — Implementation |
| `feat(...): interface skeleton` | — | — | Phase 4 — Interface skeleton | Phase 5 — Failing tests |
| `chore(...): add dependencies` | — | — | Phase 3 — Add dependencies | Phase 4 — Interface skeleton |
| `spec(...): spec approved` | — | — | Phase 2 — SPEC review | Phase 3 — Add dependencies |
| any other `spec(...): ...` commit | — | — | Phase 1 — Branch + spec | Phase 2 — SPEC review |
| (no commits since main) | — | — | (none) | Phase 1 — Branch + spec |

If the observations do not fit any row cleanly, do not guess — report what you found and ask the user which phase to resume from. A `test(...)` head commit with **mixed** failures (not all `not implemented`) is one such case — it usually means uncommitted implementer work was lost or partially committed by hand.

## Step 4 — Report and confirm

Present this and wait for explicit confirmation:

```
Resume report — feature/<slug>

Last completed phase : <phase number and name>
Resuming from        : <phase number and name>

Evidence:
- git log:  <one-line summary of relevant commits>
- tests:    <pass / FAIL (n failures) / not run> — <scoped to unit / full suite>
- PR:       <none / draft #N / open #N>

Uncommitted changes: <none / list of files>
```

Ask: "Does this look correct? Reply YES to resume, or tell me what to correct." If the user corrects the detected phase, update and re-report before proceeding.

## Step 5 — Resume the workflow

Once the user replies YES, read `.claude/orchestrator.md` and drive it from the identified phase — same caps, gates, escalation, and sub-agent contract as a fresh run, with these exceptions:

- **Do not** run Phase 1's branch setup — the worktree is already on `feature/<slug>`.
- **Do not** re-write or overwrite the spec unless the user explicitly instructs it. An approved spec is immutable — a change goes through Phase 1 supersede mode.
- **Do** apply the Phase 6 entry gate (confirm red tests via `${TEST_SCOPE_CMD}`) before invoking the implementer, even on resume.
- For a Phase 6 partial resume, pass the current test failure output as `prev_failures` in the first implementer invocation, and set `impl_iter` to 1.
- For a Phase 7 partial resume, do not push again if the branch is already on remote, and do not create a new PR if one already exists.
- Spawn workers via the Task tool without worktree isolation, so they operate in this worktree.
