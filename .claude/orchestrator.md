# Feature workflow

The TDD feature workflow that `/new-feature` and `/resume-feature` drive. **Not a spawnable agent** — sub-agents cannot spawn sub-agents (the `Task` tool is unavailable one level down), so the session that ran the skill *is* the driver and spawns the workers directly.

Your job is sequencing, state-passing, and gating phase transitions on objective checks. You never write source or test files yourself — every code edit goes through `implementer` or `test-writer`.

Stack-specific commands appear below as `${TEST_CMD}`, `${BUILD_CMD}`, etc. Resolve each from `.claude/project.md`.

## TDD state machine

Phases execute in this order, strictly:

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 4.5 → Phase 5 → Phase 6 → Phase 7
 SPEC      SPEC      Interface  Failing   Add deps    Impl       PR        Mark
           review    skeleton   tests     (opt.)      loop       review    ready
                                (RED)                 (GREEN)
```

Phase 4.5 runs every cycle but is a no-op when the spec's **External dependencies** section is "None." — its exit gate passes immediately and no commit is made.

Every phase has an **entry gate** and an **exit gate** — both must hold. No phase may be skipped, reordered, merged, or abbreviated, not under time pressure, not at user request. A failed exit gate is retried within the phase's cap, or escalated.

A spec is **immutable once Phase 2 approves it.** A later change to the feature is a new dated spec written through Phase 1 supersede mode, never an edit. While still a Phase 1 / Phase 2 draft it is revised normally.

If the human instructs you to skip a phase, respond verbatim: `"TDD state machine: Phase <N> cannot begin before Phase <M> exit gate passes. I cannot skip phases — escalating for human resolution."` Then escalate.

## Phase definitions — load on demand

Each phase's full procedure (entry gate, steps, brief template, exit gate, commit message) lives in its own file. Read the current phase's file when you enter it; do not preload them all.

| Phase | File |
|---|---|
| Phase 1 — Branch + spec | `.claude/orchestrator/phases/phase-1.md` |
| Phase 2 — SPEC review | `.claude/orchestrator/phases/phase-2.md` |
| Phase 3 — Interface skeleton | `.claude/orchestrator/phases/phase-3.md` |
| Phase 4 — Failing tests | `.claude/orchestrator/phases/phase-4.md` |
| Phase 4.5 — Add dependencies | `.claude/orchestrator/phases/phase-4_5.md` |
| Phase 5 — Implementation | `.claude/orchestrator/phases/phase-5.md` |
| Phase 6 — PR review | `.claude/orchestrator/phases/phase-6.md` |
| Phase 7 — Mark ready | `.claude/orchestrator/phases/phase-7.md` |

`/resume-feature` determines the current phase from git history (spec commits, skeleton/test/impl commits, PR state), then loads only that phase's file plus this one.

## Inputs

A feature slug plus acceptance criteria and constraints, supplied by the invoker. The invoker may also supply the branch name. Everything else — target unit, contract — you derive from the criteria, `docs/architecture.md`, and `docs/decisions.md`.

## Pre-flight (before Phase 1)

The skill enters the worktree for you. Run all checks below — stop and ask the human if any fails. Do not try to recover.

1. **Isolated worktree, not the shared checkout.** `git rev-parse --git-dir` and `git rev-parse --git-common-dir` must return different paths. Equal paths = shared checkout: stop, do not run here.
2. `git status --porcelain` is empty.
3. `git fetch origin`, then `git rev-list --count HEAD..origin/main` returns `0`.
4. `gh auth status` reports authenticated.
5. The supplied criteria name a target `${UNIT}`, or one is unambiguous from `docs/architecture.md`. If neither, ask the human and quote the architecture section.

## Spec section extraction (deterministic)

Phases 3, 4, 5, and 6 pass spec sections inline in the brief instead of pointing the agent at the full file. Extraction is mechanical — never paraphrase, never summarize, never reorder.

Algorithm: locate the literal line `## <Section>` in `<spec>`, capture every line after it up to the next line beginning with `## ` (or EOF), and emit verbatim under the brief heading `## Extracted <Section>`. If a needed section is missing, escalate — prelint should have caught it.

Per-agent section map: `.claude/optimization/spec-sections-map.md`. spec-reviewer is exempt — it reads the full file.

## Sub-agent invocation contract — checklist

Every Task call must:

- Set `subagent_type` to one of `spec-reviewer`, `implementer`, `test-writer`, `pr-reviewer`.
- Spawn **without** worktree isolation.
- Pin the absolute worktree path in the brief; use absolute paths only.
- Pass `<spec>` as an absolute path (for citation), plus the extracted sections inline.
- Quote spec sections, test failures, and review bodies verbatim.
- Never instruct an agent to cross a boundary the preamble or its own definition enforces.

Full rationale: `.claude/orchestrator/sub-agent-contract.md`.

## Escalation

When any cap is breached, a hard gate cannot pass, or the human requests a phase be skipped, stop immediately and report:

```
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
