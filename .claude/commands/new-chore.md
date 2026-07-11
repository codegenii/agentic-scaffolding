---
argument-hint: <slug or description>
description: Start an isolated chore in its own git worktree
---

You are starting a **chore** — a unit of repo work that is not a feature: refactors, docs, config, agent or workflow edits, dependency bumps. The raw argument is: `$ARGUMENTS`.

A chore runs in its own git worktree on its own branch so it never collides with parallel sessions sharing the repo. See the "Working in parallel" section of `CLAUDE.md`.

## Step 1 — Determine the slug

`$ARGUMENTS` may be an explicit `<slug>`, a `<slug>` followed by a description, or a bare description with no slug. Resolve it:

1. If `$ARGUMENTS` is empty, ask the user for a one-line description and wait.
2. Take the first whitespace-delimited token. It is an **explicit slug** when it is valid kebab-case — only `a-z`, `0-9`, `-` — **and** it is either the only token or contains a `-`. Then the slug is that token, and any remaining text is the description.
3. Otherwise treat all of `$ARGUMENTS` as the description and **derive** the slug: two-to-five meaningful words, lowercased, filler words dropped, joined with `-`.
4. If an explicit slug was supplied but is not valid kebab-case, stop and tell the user:

   > "Invalid slug `<value>`. A slug must be lowercase kebab-case (e.g. `bump-deps`). Re-run with a corrected slug."

5. State the slug you will use, noting whether it was supplied or derived, so the user can correct it. Then proceed.

## Step 2 — Enter an isolated worktree

Call `EnterWorktree` to create a fresh worktree branched from `origin/main`. This skill is the explicit instruction that authorizes the tool — the current working tree need not be clean or on `main`, since the worktree is cut from `origin/main` regardless.

If `EnterWorktree` reports the session is already in a worktree, stop and tell the user to run `/new-chore` from a normal session.

Before touching any branch, confirm `EnterWorktree` actually isolated the session: `git rev-parse --git-dir` and `git rev-parse --git-common-dir` must return different paths. If they are equal, you are in the shared checkout: stop immediately and do not run `git branch -m`.

Inside the worktree, rename its branch to `chore/<slug>`:

- If a branch named `chore/<slug>` already exists, stop and tell the user — do not reuse or overwrite it.
- Otherwise run `git branch -m chore/<slug>` to rename the worktree's own branch in place.

## Step 3 — Do the chore

Use the description resolved in Step 1. If no description was given, ask the user what the chore is and wait.

Carry out the chore in the worktree. Keep it to the stated scope. A chore is not a feature — do not invoke the orchestrator or run the TDD state machine.

## Step 4 — Finish

1. Commit on `chore/<slug>` with a `chore(<scope>): <summary>` subject per `.claude/agents/_conventions-reference.md` — subject only, no body. `<scope>` is a short topical word, not the full slug.
2. Report the branch as unpushed and unmerged. Merging is a human decision — never merge or open a PR unless the user explicitly asks.
3. Run `./scripts/sync-worktree-permissions.sh` to promote permissions approved during this chore into the main checkout.
4. Call `ExitWorktree` with `action: "keep"`, so the branch and its commits remain for the user to review and land.
