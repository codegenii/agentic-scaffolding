# Phase 2 — SPEC review

**Entry gate:** Phase 1 exit gate passed. Zero source or test files in the target `${UNIT}`.

**Step 1 — Automated.** Invoke `spec-reviewer`:

> Review the spec for the `<slug>` feature. The spec file is at `<spec>`.

- **REQUEST CHANGES**: revise `<spec>`, commit (`spec(<slug>): address spec-review`), re-invoke. Cap 3 rounds, then escalate.
- **APPROVE**: continue to Step 2.

**Step 2 — Human.** Present `<spec>` and the verdict, then ask:

> "The spec has been approved by spec-reviewer. Please confirm it correctly captures your intent before any code is written. Reply APPROVED to continue, or provide feedback to incorporate."

- APPROVED: proceed to Phase 3.
- Feedback: revise, re-run spec-reviewer (counts against the same cap of 3), re-present.
- Skip request: respond that spec-review cannot be skipped.

**Exit gate:** spec-reviewer is APPROVE **and** human is APPROVED. No source or test code written. The spec is now immutable.

`git add <spec> && git commit --allow-empty -m "spec(<slug>): spec approved"`. The commit always lands, even when the spec was not revised since Phase 1 — it is the marker that resume-feature uses to tell "Phase 2 done" from "Phase 1 done only".

**Post-marker, pre-Phase-3 revision.** Until Phase 3 begins (no dependency, source, or test changes yet), a human may still request a behavior change without a supersede: revise the spec, re-run Steps 1–2, re-commit the marker. Duplicate markers are expected — the latest wins. From Phase 3 on, the spec is immutable and changes supersede through Phase 1.
