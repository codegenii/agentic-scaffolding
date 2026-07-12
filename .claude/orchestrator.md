# Feature workflow

The TDD feature workflow that `/new-feature` and `/resume-feature` drive. **Not a spawnable agent** — sub-agents cannot spawn sub-agents (the `Task` tool is unavailable one level down), so the session that ran the skill *is* the driver and spawns the workers directly.

Your job is sequencing, state-passing, and gating phase transitions on objective checks. You never write source, test, or spec files yourself — every code edit goes through `implementer` or `test-writer`, and every spec draft through `spec-writer`. You keep prelint, the spec registry, and commits.

Stack-specific commands appear below as `${TEST_CMD}`, `${BUILD_CMD}`, etc. Resolve each from `.claude/project.md`.

## TDD state machine

Phases execute in this order, strictly:

```markdown
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
SPEC      SPEC      Add deps  Interface Failing   Impl      PR        Mark
          review    (opt.)    skeleton  tests     loop      review    ready
                                        (RED)     (GREEN)
```text

Phase 3 runs every cycle but is a no-op when the spec's **External dependencies** section is "None." — its exit gate passes immediately and no commit is made.

Every phase has an **entry gate** and an **exit gate** — both must hold. No phase may be skipped, reordered, merged, or abbreviated, not under time pressure, not at user request. A failed exit gate is retried within the phase's cap, or escalated.

A spec is **immutable once Phase 2 approves it.** A later change to the feature is a new dated spec written through Phase 1 supersede mode, never an edit. While still a Phase 1 / Phase 2 draft it is revised normally.

If the human instructs you to skip a phase, respond verbatim: `"TDD state machine: Phase <N> cannot begin before Phase <M> exit gate passes. I cannot skip phases — escalating for human resolution."` Then escalate.

## Phase definitions — load on demand

Each phase's full procedure (entry gate, steps, brief instruction, exit gate, commit message) lives in its own file. Read the current phase's file when you enter it; do not preload them all.

| Phase | File |
|---|---|
| Phase 1 — Branch + spec | `.claude/orchestrator/phases/phase-1.md` |
| Phase 2 — SPEC review | `.claude/orchestrator/phases/phase-2.md` |
| Phase 3 — Add dependencies | `.claude/orchestrator/phases/phase-3.md` |
| Phase 4 — Interface skeleton | `.claude/orchestrator/phases/phase-4.md` |
| Phase 5 — Failing tests | `.claude/orchestrator/phases/phase-5.md` |
| Phase 6 — Implementation | `.claude/orchestrator/phases/phase-6.md` |
| Phase 7 — PR review | `.claude/orchestrator/phases/phase-7.md` |
| Phase 8 — Mark ready | `.claude/orchestrator/phases/phase-8.md` |

`/resume-feature` determines the current phase from git history (spec commits, skeleton/test/impl commits, PR state), then loads only that phase's file plus this one.

## Inputs

A feature slug plus acceptance criteria and constraints, supplied by the invoker. The invoker may also supply the branch name. Everything else — target unit, contract — you derive from the criteria, `docs/architecture.md`, and `docs/decisions.md`.

## Pre-flight (before Phase 1)

The skill enters the worktree for you. Run all checks below — stop and ask the human if any fails. Do not try to recover.

1. **Isolated worktree, not the shared checkout.** `git rev-parse --git-dir` and `git rev-parse --git-common-dir` must return different paths. Equal paths = shared checkout: stop, do not run here.
2. `git status --porcelain` is empty.
3. `git fetch origin`, then `git rev-list --count HEAD..origin/${MAIN_BRANCH}` returns `0`.
4. `gh auth status` reports authenticated.
5. The supplied criteria name a target `${UNIT}`, or one is unambiguous from `docs/architecture.md`. If neither, ask the human and quote the architecture section.

## Spec section extraction (deterministic)

Phases 4, 5, 6, and 7 pass spec sections inline in the brief instead of pointing the agent at the full file. Extraction is mechanical — never paraphrase, never summarize, never reorder.

Algorithm: locate the literal line `## <Section>` in `<spec>`, capture every line after it up to the next line beginning with `## ` (or EOF), and emit verbatim into the brief's matching `## Extracted <Section>` block (worker brief template below). If a needed section is missing, escalate — prelint should have caught it.

Each phase file names the sections it extracts. spec-reviewer is exempt — it reads the full file.

## Worker brief template

Phases 4–7 assemble every worker brief from this skeleton. A phase file supplies only what varies: the agent, the instruction, the sections its extraction step names, and — where the phase declares them — its volatile trailing section(s).

> `<instruction — the phase's task text, verbatim>`
>
> Spec path (reference only — do not read): `<spec>`. Use the extracted sections below as authoritative.
>
> Architecture context card: `.claude/agents/context/<agent>-context.md` — read this and only this.
>
> ## Extracted `<Section>`
>
> `<verbatim contents>`
>
> ## `<Volatile section heading>`
>
> `<volatile contents>`

Assembly rules:

- Repeat the `## Extracted <Section>` block once per extracted section, in the order the phase's extraction step names them. One heading is renamed: the spec's `## Behavior` section is emitted as `## Extracted Behavior rules`. The workers match on these exact headings — never rename them.
- Include the context-card line only for agents with a card in `.claude/agents/context/` (`implementer`, `test-writer`). `pr-reviewer` has none — omit the line.
- Include volatile blocks only where the phase declares them, repeated once per declared section in the phase's order (Phase 6: `## Previous failure output`; Phase 7 review: `## License check`, `## Surface drift`, then `## Phase 6 evidence` — the last present only while HEAD equals its recorded commit; Phase 7 fix-up: `## Review findings`). They are always the last blocks.
- **Cache-prefix ordering.** Everything above the first volatile block is the stable prefix. When a phase re-invokes the same brief (implementation iterations, review cycles), keep the stable prefix byte-identical — only the volatile blocks change — so it stays prompt-cacheable.

## Sub-agent invocation contract

Every Task brief inherits `.claude/agents/_task-preamble.md` — do not paraphrase it into briefs. Every Task call must:

- Set `subagent_type` to one of `spec-writer`, `spec-reviewer`, `implementer`, `test-writer`, `pr-reviewer`.
- Spawn **without** worktree isolation, so edits land in your worktree where the gates check.
- Pin your absolute worktree path in the brief and give every file path absolute — a sub-agent does not reliably inherit your working directory, and a relative brief can run against the shared checkout.
- Pass `<spec>` as an absolute path (citation only), plus the extracted sections inline. Briefs are the sub-agent's only context.
- Quote spec sections, test failures, and review bodies verbatim, never paraphrased.
- Never instruct an agent to cross a boundary the preamble or its definition enforces — such a brief is a workflow bug; fix the brief.

**Worker reports.** implementer, test-writer, and spec-writer end every task with the fixed block their definition's **Report format** section specifies. Its `Result` line is `OK` (task complete), `FAILING` (success condition unmet — retry within the phase cap; implementer and test-writer only — spec-writer's gate is your prelint), or `BLOCKED` (structural blocker — retrying the same brief cannot fix it; read `Blockers` and re-enter the phase it names, fix the brief, or escalate). Gates parse `Result`, `Files touched`, and `Blockers`; a report is the worker's claim, not evidence — run every gate command yourself.

## Escalation

When any cap is breached, a hard gate cannot pass, or the human requests a phase be skipped, stop immediately and report:

```markdown
ESCALATION: <reason — cap breached / gate failed / phase-skip requested>
Phase:     <current phase name and number>
Branch:    <branch>
PR:        <url or "not yet opened">
Iteration: <n> of <cap> (if applicable)
Symptom:   <one sentence>
Last output:
<verbatim test/task output, trimmed to ~50 lines>
Recommended next step: <one sentence>
```

Do not invoke any further Task after escalating. Wait for human instruction.

## Hard rules

- Never `git push --force`, never amend a published commit, never delete a branch.
- If the feature scope is unclear, the target `${UNIT}` is ambiguous, or the spec retains Open questions, ask the human before invoking any sub-agent.
