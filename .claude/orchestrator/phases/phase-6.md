# Phase 6 — Implementation (cap: 5 iterations)

**Entry gate:** Phase 5 exit gate passed. Mandatory TDD pre-check — run `${TEST_SCOPE_CMD}`:

- Exit non-zero **and** at least one failure line contains `not implemented` → proceed.
- Already green → **escalate immediately**, no red tests to drive implementation.
- Compile/load errors instead of `not implemented` → **escalate immediately**, broken suite belongs in Phase 5.

Initialize `impl_iter = 0`, `prev_failures = ""`.

**Each iteration:**

1. `impl_iter += 1`. If `> 5`, escalate.
2. Invoke `implementer` with the worker brief template (`orchestrator.md`). On the first iteration extract `## Interface contract` and `## Behavior` from `<spec>` verbatim; reuse the same extracted text on subsequent iterations. Volatile section `## Previous failure output`: `<prev_failures or "first attempt">`. Instruction:

   > Implement the target `<unit>` to pass `${TEST_SCOPE_CMD}`. Run the test suite after each edit. Iterate until green.

   Keep everything above `## Previous failure output` byte-identical across iterations — only the failure section changes, so the stable prefix stays prompt-cacheable across the up-to-5 invocations.

3. Read the implementer report. `Result: BLOCKED` (e.g. a `SPEC MISMATCH` under `Blockers`) → escalate immediately; iterating cannot clear a blocker. `OK` or `FAILING` → continue; your own runs below decide.
4. Run `${TEST_SCOPE_CMD}`.
5. Green: run `${LINT_CMD}`, then `${BUILD_CMD}` (skip either set to `none`; build runs here so the evidence block below covers the whole toolchain). Both clean → `git add <unit> && git commit -m "feat(<unit>): implementation"`, record the evidence block, proceed to Phase 7. Lint or build issues → next iteration's failure input.
6. Red: capture failures. Identical failing-test set for two consecutive iterations → escalate (implementer not making progress). Otherwise update `prev_failures` and loop.

**Phase 6 evidence block.** Assemble after the implementation commit, from your own step 4–5 runs — never from the implementer report:

```text
commit: <git rev-parse HEAD>
test-scope (<resolved ${TEST_SCOPE_CMD}>): exit 0
lint (<resolved ${LINT_CMD}>): exit 0, or none
build (<resolved ${BUILD_CMD}>): exit 0, or none
```

Hold it in session state for Phase 7, which passes it in the pr-reviewer brief; SHA-matched, it lets the reviewer credit these runs instead of repeating build and lint. It is never committed — if the session ends before the first review, it is simply absent and the reviewer runs the full toolchain itself.

**Exit gate:** the last implementer report shows `Result: OK`; `${TEST_SCOPE_CMD}` exits 0, `${LINT_CMD}` is clean (or `none`), and `${BUILD_CMD}` exits 0 (or `none`) — your own runs from steps 4–5, not the report's `Commands` lines.
