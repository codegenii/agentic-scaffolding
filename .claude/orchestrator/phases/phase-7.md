# Phase 7 — PR review (cap: 2 request-changes cycles)

**Entry gate:** Phase 6 exit gate passed. Implementation committed.

On first entry only:
1. `git push -u origin HEAD`.
2. If `gh pr view --json number 2>/dev/null` is empty: `gh pr create --draft --title "<feature title>" --body "<one-line summary from the spec's Purpose>"`. Derive `<feature title>` from the slug and Purpose.

Initialize `review_iter = 0`.

**Each cycle:**
1. Extract verbatim the `## Purpose`, `## Interface contract`, `## Behavior`, `## Out of scope`, and `## External dependencies` sections of `<spec>`. Invoke `pr-reviewer`:

   > Review the open draft PR for branch `<branch>`. Run the toolchain, diff against main, and post a single structured review via `gh pr review`.
   >
   > Spec path (reference only — do not read): `<spec>`. Use the extracted sections below as authoritative for SPEC-compliance checks.
   >
   > ## Extracted Purpose
   > <verbatim contents>
   >
   > ## Extracted Interface contract
   > <verbatim contents>
   >
   > ## Extracted Behavior rules
   > <verbatim contents>
   >
   > ## Extracted Out of scope
   > <verbatim contents>
   >
   > ## Extracted External dependencies
   > <verbatim contents>

2. Read the latest verdict: `gh pr view --json reviews -q '.reviews[-1].state'`.
3. `APPROVED` or `COMMENTED` → Phase 8.
4. `CHANGES_REQUESTED`:
   - `review_iter += 1`. If `> 2`, escalate.
   - Body: `gh pr view --json reviews -q '.reviews[-1].body'`.
   - Invoke `implementer` (reuse the extracted `## Interface contract` and `## Behavior` from Phase 6):

     > The PR reviewer requested changes on the draft PR. Address each finding. Run `${TEST_SCOPE_CMD}` and `${LINT_CMD}` and confirm both clean before stopping. Findings: `<paste verbatim>`.
     >
     > Spec path (reference only — do not read): `<spec>`. Use the extracted sections below as authoritative.
     >
     > ## Extracted Interface contract
     > <verbatim contents>
     >
     > ## Extracted Behavior rules
     > <verbatim contents>

   - Run `${TEST_SCOPE_CMD}` yourself. Green → `git commit -am "fix(<unit>): address review" && git push`, loop. Red → feed the failure into another implementer iteration (counts against `review_iter`).

**Exit gate:** Verdict is `APPROVED` or `COMMENTED`.
