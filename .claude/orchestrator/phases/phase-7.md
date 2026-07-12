# Phase 7 — PR review (cap: 2 request-changes cycles)

**Entry gate:** Phase 6 exit gate passed. Implementation committed.

On first entry only:

1. `git push -u origin HEAD`.
2. If `gh pr view --json number 2>/dev/null` is empty: `gh pr create --draft --title "<feature title>" --body "<one-line summary from the spec's Purpose>"`. Derive `<feature title>` from the slug and Purpose.

Initialize `review_iter = 0`.

**Each cycle:**

1. Idempotency guard: if the latest review's commit (`gh pr view --json reviews -q '.reviews[-1].commit.oid'`) equals `git rev-parse HEAD`, do not re-invoke pr-reviewer — read that verdict and continue at step 2. Otherwise run the two driver-side check scripts from the worktree root, capturing each output verbatim:

   - `./scripts/check-licenses.sh ${MAIN_BRANCH}` → the `## License check` block.
   - `./scripts/surface-drift.sh ${MAIN_BRANCH}` → the `## Surface drift` block.

   Exit 2 from either script is a configuration bug (a `project.md` value missing or still a placeholder) — escalate. Exit 0 or 1: include the output; the verdict belongs to the reviewer.

   Then extract verbatim the `## Purpose`, `## Interface contract`, `## Behavior`, `## Out of scope`, and `## External dependencies` sections of `<spec>` and invoke `pr-reviewer` with the worker brief template (`orchestrator.md`). Instruction:

   > Review the open draft PR for branch `<branch>`. Verify the toolchain — run it yourself, or credit the driver-run commands in the `## Phase 6 evidence` section per your evidence rules when one is present below. The `## License check` and `## Surface drift` sections below are driver-run script output — transcribe them per your steps, do not redo them. Diff against ${MAIN_BRANCH} and post a single structured review via `gh pr review`. The extracted sections below are authoritative for SPEC-compliance checks.

   Volatile sections, the last blocks of the brief in this order:

   - `## License check` — script output verbatim, every cycle.
   - `## Surface drift` — script output verbatim, every cycle.
   - `## Phase 6 evidence` — the block recorded at Phase 6 exit, only if `git rev-parse HEAD` still equals its `commit` line; otherwise omit the section entirely — after a fix-up commit the reviewer must re-run the full toolchain, and a resumed session that never recorded the block must not reconstruct one from git history.

   Everything above `## License check` stays byte-identical across cycles (stable prefix, prompt-cacheable).

2. Read the latest verdict: `gh pr view --json reviews -q '.reviews[-1].state'`.
3. `APPROVED` or `COMMENTED` → Phase 8.
4. `CHANGES_REQUESTED`:
   - `review_iter += 1`. If `> 2`, escalate.
   - Body: `gh pr view --json reviews -q '.reviews[-1].body'`.
   - Invoke `implementer` with the worker brief template (reuse the extracted `## Interface contract` and `## Behavior` from Phase 6). Volatile section `## Review findings`: the review body, pasted verbatim. Instruction:

     > The PR reviewer requested changes on the draft PR. Address each finding in the review below. Run `${TEST_SCOPE_CMD}` and `${LINT_CMD}` and confirm both clean before stopping.

     Volatile content (the findings) goes last so the brief's stable prefix stays prompt-cacheable across cycles.

   - If the implementer report is `Result: BLOCKED`, escalate — a review finding that contradicts the spec needs human resolution.
   - Run `${TEST_SCOPE_CMD}` yourself. Green → `git commit -am "fix(<unit>): address review" && git push`, loop. Red → feed the failure into another implementer iteration (counts against `review_iter`).

**Exit gate:** Verdict is `APPROVED` or `COMMENTED`.
