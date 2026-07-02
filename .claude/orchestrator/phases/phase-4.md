# Phase 4 — Failing tests (cap: 2 retries)

**Entry gate:** Phase 3 exit gate passed. `${BUILD_CMD}` exits 0 (or is `none`). No test files (matching `${TEST_GLOB}`) in the target `${UNIT}` (excluding pre-existing unrelated).

**Pre-brief extraction.** Read `<spec>`. Extract verbatim the `## Interface contract`, `## Behavior`, and `## Test strategy` sections. Pass inline.

Invoke `test-writer`:

> Read the interface files in `<unit>`. Write table-driven test files covering every function and method: happy path, every edge case implied by the spec, and every declared error condition. Honor the extracted **Test strategy** below — gate integration-classified tests per `${INTEGRATION_GATE}` in `.claude/project.md`. Confirm `${TEST_SCOPE_CMD}` (unit-tagged suite only) fails with `not implemented` on every test, never with a compile/load error.
>
> Spec path (reference only — do not read): `<spec>`. Use the extracted sections as authoritative.
>
> Architecture context card: `.claude/agents/context/test-writer-context.md` — read this and only this.
>
> ## Extracted Interface contract
> <verbatim contents>
>
> ## Extracted Behavior rules
> <verbatim contents>
>
> ## Extracted Test strategy
> <verbatim contents>

If test-writer returns `BUILD FAILURE: interfaces not ready for testing`, re-enter Phase 3 with the error (counts against Phase 3's cap).

**Exit gate:**
- `git diff --stat` shows only test files (matching `${TEST_GLOB}`) under `<unit>`.
- `${TEST_SCOPE_CMD}` (unit suite) exits non-zero.
- Every failure line contains `not implemented`. A compile/load error here is a hard failure — re-invoke test-writer with the output.
- Failing-test count covers every behavior classified **unit** in the spec's Test strategy. Integration-only behaviors are exempt.
- If the spec declares integration tests, confirm they are gated per `${INTEGRATION_GATE}` and are not run by the unit suite.

After 2 retries, escalate.

`git add <unit> && git commit -m "test(<unit>): failing suite"`
