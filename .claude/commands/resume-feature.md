---
argument-hint: <slug>
description: Resume an interrupted feature workflow
---

You are resuming an interrupted feature workflow. The raw argument is: `$ARGUMENTS`. The workflow runs in **this** session — there is no separate "orchestrator" agent to spawn.

## Step 1 — Validate the slug

Extract the slug from `$ARGUMENTS` (first whitespace-delimited token). A valid slug is lowercase kebab-case. If invalid, stop:

> "Invalid slug `<value>`. Must be lowercase kebab-case (e.g. `user-auth-refresh`)."

## Step 2 — Enter the feature's worktree

The branch `feature/<slug>` already exists from the interrupted run. Put this session in an isolated worktree on it:

1. Run `git fetch origin`. If neither a local `feature/<slug>` nor `origin/feature/<slug>` exists, stop:
   ```
   RESUME ERROR: branch feature/<slug> does not exist. Nothing to resume.
   ```
2. Run `git worktree add .claude/worktrees/resume-<slug> feature/<slug>`. If it fails because the branch is already checked out elsewhere, stop and tell the user to free that worktree first.
3. Call `EnterWorktree` with `path: .claude/worktrees/resume-<slug>` to switch this session into the worktree. This skill is the explicit instruction that authorizes the tool.
4. If `git status --porcelain` is non-empty, stop and report the uncommitted changes verbatim. Do not proceed until the working tree is clean.

## Step 3 — Detect the current phase

Run these and record all output:

1. `git log --oneline main..HEAD` — commits on this branch since it diverged from main.
2. `${TEST_CMD}` — full output and exit code.
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
- tests:    <pass / FAIL (n failures) / not run>
- PR:       <none / draft #N / open #N>

Uncommitted changes: <none / list of files>
```

Ask: "Does this look correct? Reply YES to resume, or tell me what to correct." If the user corrects the detected phase, update and re-report before proceeding.

## Step 5 — Resume the workflow

Once the user replies YES, read `.claude/orchestrator.md` and drive it from the identified phase — same caps, gates, escalation, and sub-agent contract as a fresh run, with these exceptions:

- **Do not** run Phase 1's branch setup — the worktree is already on `feature/<slug>`.
- **Do not** re-write or overwrite the spec unless the user explicitly instructs it. An approved spec is immutable — a change goes through Phase 1 supersede mode.
- **Do** apply the Phase 6 entry gate (confirm red tests via `${TEST_CMD}`) before invoking the implementer, even on resume.
- For a Phase 6 partial resume, pass the current test failure output as `prev_failures` in the first implementer invocation, and set `impl_iter` to 1.
- For a Phase 7 partial resume, do not push again if the branch is already on remote, and do not create a new PR if one already exists.
- Spawn workers via the Task tool without worktree isolation, so they operate in this worktree.
