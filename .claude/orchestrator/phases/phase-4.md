# Phase 4 — Interface skeleton (cap: 2 retries)

**Entry gate:** Phase 3 exit gate passed. Zero source files in the target `${UNIT}` (excluding pre-existing unrelated files).

**Pre-brief extraction.** Read `<spec>`. Extract verbatim the `## Interface contract` and `## Behavior` sections (every line after the heading up to the next `## `). Pass these inline in the brief — do not paraphrase, do not summarize.

Invoke `implementer` with the worker brief template (`orchestrator.md`). Instruction:

> Produce only the interfaces, types, exported errors, and function/method stubs declared in the spec's **Interface contract**. Each body is the project's `${NOT_IMPL}` idiom (see `.claude/project.md`). Do not implement logic.

**Exit gate:**
- The implementer report shows `Mode: interface-only`, `Result: OK`, `Blockers: None.`
- `git diff --stat` shows only the target `${UNIT}`, no test files (matching `${TEST_GLOB}`), and agrees with the report's `Files touched`.
- `${BUILD_CMD}` exits 0 (skip if `${BUILD_CMD}` is `none`) — your own run, not the report's `Commands` line.
- Every exported symbol named in the spec's Interface contract appears in the diff.

On failure, re-invoke quoting the gap. After 2 retries, escalate.

`git add <unit> && git commit -m "feat(<unit>): interface skeleton"`
