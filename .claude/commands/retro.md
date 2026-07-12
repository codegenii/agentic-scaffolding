# /retro — process retrospective

**Model:** Sonnet &nbsp;**Effort:** medium — read only what the heuristics below flag; do not scan the full codebase.

## Purpose

Bounded retrospective: scan recent git history for corrective signals, check them against the project invariants, propose at most 3 small fixes, apply each as a tiny commit on a `chore/retro-<date>` branch.

## Step 1 — Determine the log window

Find the most recent commit whose subject starts with `chore(retro)`:

```bash
git log --oneline | grep -m1 "chore(retro)" | awk '{print $1}'
```

If a hash is found, the window is `<hash>..HEAD`. Otherwise use the last 30 commits (`HEAD~30..HEAD`, or all commits if fewer). Store the base ref.

## Step 2 — Collect corrective signals

Run each of the following. Record every match.

**2a. Reverts in the window:**
```bash
git log <base>..HEAD --oneline | grep -i "^[0-9a-f]* revert"
```

**2b. Corrective-word commits (drop / clarify / align / never / rejected):**
```bash
git log <base>..HEAD --oneline | grep -iE "(drop|clarify|align|never|rejected)"
```

**2c. Spec files edited after an approval commit (same slug):**
```bash
git log <base>..HEAD --oneline --diff-filter=M -- "docs/specs/*.md"
```
For each changed spec, check whether a commit with `approved` in its subject on the same slug appears *before* the edit. Flag any that do — an approved spec is immutable.

**2d. Invariant-contradiction sweep in docs changed in the window:**
```bash
git diff <base>..HEAD --name-only -- docs/
```
Read `.claude/agents/conventions/invariants.md`. For each invariant, derive the words that would signal a violation (e.g. an invariant forbidding network on the default path → grep for the relevant client/API names) and grep the changed docs' hunks for them. Flag any hit that contradicts an invariant. Also read `CLAUDE.md` for any stated hard rules and check the same way.

**2e. Re-duplicated invariants outside the canonical file:**
```bash
grep -rniE "^#+ .*invariant|project-specific invariant" .claude/agents/ | grep -v "conventions/invariants.md"
```
Flag any hit that copies a rule from `conventions/invariants.md` back into a role file — that is the single-source consolidation drifting back. `_conventions.md`'s "Always-applicable invariants" heading is the known exception.

## Step 3 — Propose at most 3 improvements

From the signals, select at most 3 improvements. Each must be completable as a single tiny commit — a doc fix, an invariant addition, a guard, a memory entry. Never propose a redesign or new feature. If no signals were flagged, report "no signals found — nothing to improve" and stop.

Present the proposals with a one-line rationale each. Ask the user to approve before applying.

## Step 4 — Enter worktree and apply

Once approved, determine today's date (YYYY-MM-DD) and enter a worktree:

```
EnterWorktree name="retro-<date>"
```

Then run `./scripts/setup-worktree.sh` to inherit the main checkout's permission grants; a failure is non-fatal — note it and continue.

Rename its branch: `git branch -m chore/retro-<date>`.

Apply each approved improvement as its own commit with subject `chore(retro): <short description>`. No body.

When all commits are done, report the branch as **ready to merge**. Do not merge, push, or open a PR. Run `./scripts/sync-worktree-permissions.sh` and call `ExitWorktree action="keep"`.
