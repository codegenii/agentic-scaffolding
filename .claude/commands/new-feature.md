---
argument-hint: <slug> [criteria and constraints] [use haiku | use opus]
description: Start a new feature workflow
---

You are starting a new feature workflow. The raw argument is: `$ARGUMENTS`.

## Step 0 — Driver model gate

The driver holds the workflow's guardrails — worktree discipline, phase gates — across the longest transcript in the system, and instruction adherence decays with transcript depth, steeply on small models, so features are driven on **sonnet** by default. `use haiku` (or `--haiku`) opts down for short, shallow-transcript runs; `use opus` (or `--opus`) opts up. The canonical position is immediately after the slug, before the criteria — `/new-feature rate-limiter use haiku Per-IP rate limiting on the public API.` — but honor the directive anywhere in the arguments.

1. Resolve the requested driver model from `$ARGUMENTS`: `haiku` if it contains `use haiku` or `--haiku`, `opus` if it contains `use opus` or `--opus`, otherwise `sonnet` (`use sonnet` / `--sonnet` states the default explicitly).
2. Compare against the model this session runs on (your system prompt names it). The expectation is a **floor**, matched by family: rank haiku < sonnet < opus, any higher tier above opus. The session passes when its family ranks at or above the requested model — a stronger session is the operator's deliberate cost choice, not a mismatch.
3. If the session ranks below the requested model, stop before touching anything — you cannot switch the session model yourself — and tell the user:

   > "This run expects the driver on `<requested model>` or stronger (default sonnet; `use haiku` opts down, `use opus` opts up), but this session runs on `<session model>` — a command cannot switch the session's model. Run `/model <requested model>`, then re-run this exact `/new-feature` command."

4. On match, strip the model directive from the argument text so it does not leak into the acceptance criteria, then proceed.

## Step 1 — Validate the slug

Extract the slug: the first whitespace-delimited token in `$ARGUMENTS`. A valid slug is lowercase kebab-case — only `a-z`, `0-9`, and `-`. No spaces, no underscores, no uppercase.

If the slug is invalid, stop immediately and tell the user:

> "Invalid slug `<value>`. A slug must be lowercase kebab-case (e.g. `user-auth-refresh`). Re-run with a corrected slug."

Do not proceed until the slug is valid.

## Step 2 — Collect acceptance criteria and constraints

If `$ARGUMENTS` contains only the slug, ask the user:

> **Acceptance criteria** — testable statements that must be true for this feature to be complete.
> **Constraints** — what the implementation must not do, must preserve, or must stay compatible with.

If additional text was supplied after the slug, treat it as the acceptance criteria and constraints and skip asking. Wait for complete answers before proceeding.

## Step 3 — Confirm scope before drafting the spec

Catch scope creep here, before the worktree exists. Read `docs/architecture.md` and `CLAUDE.md`, then list what the ask implies:

- **Units touched** — one `${UNIT}` by default, more than one needs justification.
- **New surface** — interfaces, types, errors, commands.
- **Extension points touched** — any pluggable interface or seam the project marks as load-bearing.
- **New dependencies** (`${DEP_MANIFEST}`).
- **Adjacent work the ask pulls in** — config, glue, follow-on commands. Include items you would argue belong.

Present the list and ask the user to confirm or narrow it. Anything dropped will not appear in the spec. If the user narrows, replace Step 2's criteria with the narrowed version, and record every dropped item as **dropped scope** — it lands in the spec's Out of scope section so the next session has the receipt. Do not isolate a worktree until the user replies.

## Step 4 — Drive the feature workflow

The feature workflow runs in **this** session — there is no separate "orchestrator" agent to spawn. Only the top-level session can spawn the `spec-writer`, `spec-reviewer`, `implementer`, `test-writer`, and `pr-reviewer` worker agents, so this session drives the workflow itself.

1. Call `EnterWorktree` to isolate this session in a fresh worktree branched from `origin/${MAIN_BRANCH}`. This skill is the explicit instruction that authorizes the tool. If `EnterWorktree` reports the session is already in a worktree, stop and tell the user to run `/new-feature` from a normal session. Then run `./scripts/setup-worktree.sh` to inherit the main checkout's permission grants; a failure is non-fatal — note it and continue.
2. Read `.claude/orchestrator.md` — the feature workflow — and drive it yourself, Phases 1 through 8. Its Phase 1 renames the worktree's branch to `feature/<slug>`.
3. Use these inputs:
   - **slug** — `<slug>`, used as-is for the branch name `feature/<slug>`.
   - **acceptance criteria** — the text from Step 2 (narrowed if Step 3 narrowed it). These become the **Behavior** rules of the spec.
   - **constraints** — the text from Step 2. These become the **Out of scope** and constraint notes in the **Interface contract**.
   - **dropped scope** — items narrowed out in Step 3, if any. These prepopulate the spec's **Out of scope** section.
4. Spawn `spec-writer` / `spec-reviewer` / `implementer` / `test-writer` / `pr-reviewer` via the Task tool as the workflow directs — without worktree isolation, so they operate in this worktree. Every Task brief inherits `.claude/agents/_task-preamble.md` — consult the orchestrator's "Sub-agent invocation contract" before composing one.

Follow the state machine exactly — no skipped or reordered phases.
