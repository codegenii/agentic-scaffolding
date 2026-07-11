# Phase 6 — Implementation (cap: 5 iterations)

**Entry gate:** Phase 5 exit gate passed. Mandatory TDD pre-check — run `${TEST_SCOPE_CMD}`:

- Exit non-zero **and** at least one failure line contains `not implemented` → proceed.
- Already green → **escalate immediately**, no red tests to drive implementation.
- Compile/load errors instead of `not implemented` → **escalate immediately**, broken suite belongs in Phase 5.

Initialize `impl_iter = 0`, `prev_failures = ""`.

**Each iteration:**

1. `impl_iter += 1`. If `> 5`, escalate.
2. Invoke `implementer` (on first iteration extract `## Interface contract` and `## Behavior` from `<spec>` verbatim; reuse the same extracted text on subsequent iterations):

   > Implement the target `<unit>` to pass `${TEST_SCOPE_CMD}`. Run the test suite after each edit. Iterate until green.
   >
   > Spec path (reference only — do not read): `<spec>`. Use the extracted sections below as authoritative.
   >
   > Architecture context card: `.claude/agents/context/implementer-context.md` — read this and only this.
   >
   > ## Extracted Interface contract
   >
   > `<verbatim contents>`
   >
   > ## Extracted Behavior rules
   >
   > `<verbatim contents>`
   >
   > ## Previous failure output
   >
   > `<prev_failures or "first attempt">`

   Keep everything above `## Previous failure output` byte-identical across iterations — only the failure section changes, so the stable prefix stays prompt-cacheable across the up-to-5 invocations.

3. Run `${TEST_SCOPE_CMD}`.
4. Green: run `${LINT_CMD}` (skip if `none`). Clean → `git add <unit> && git commit -m "feat(<unit>): implementation"`, proceed to Phase 7. Lint issues → next iteration's failure input.
5. Red: capture failures. Identical failing-test set for two consecutive iterations → escalate (implementer not making progress). Otherwise update `prev_failures` and loop.

**Exit gate:** `${TEST_SCOPE_CMD}` exits 0 and `${LINT_CMD}` is clean (or `none`).
