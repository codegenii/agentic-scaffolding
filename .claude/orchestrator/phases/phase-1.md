# Phase 1 — Branch + spec

**Entry gate:** Pre-flight passed.

1. Use the `<slug>` supplied by the invoker as-is — already lowercase kebab-case.
2. Set `<spec>` to `docs/specs/<YYYY-MM-DD>-<slug>.md`. This path is passed to every sub-agent.
3. Put the worktree onto `<branch>` (invoker-supplied, else `feature/<slug>`). Run `git branch --show-current`:
   - detached HEAD → `git checkout -b <branch>`
   - any branch other than `${MAIN_BRANCH}` → `git branch -m <branch>` (renames in place, leaves no throwaway)
   - `${MAIN_BRANCH}` → escalate, you were not given an isolated worktree

   If `<branch>` already exists the command fails — escalate, do not reuse or overwrite.
4. Read `docs/architecture.md` (the index) and `docs/decisions.md` to confirm the target `${UNIT}`, interface, and constraints in scope. From the index, follow the pointer to the subsystem doc(s) your feature targets — read only what is relevant.
5. **Supersede check.** Read `docs/specs/README.md` (treat absent as empty). If it lists a spec whose slug matches — or whose topic the human confirms is the same feature — this run supersedes it.
   - Ask verbatim: `"An existing spec covers this topic: <original-path>. Specs are immutable — this run will write a new spec that supersedes it and mark the original superseded in the registry. Confirm supersession? Reply CONFIRM, or tell me this is a distinct feature."`
   - On CONFIRM: set `<supersedes>` to `<original-path>`.
   - "Distinct feature": escalate — slug collides, must be changed.
   - No match: `<supersedes>` is none.
6. **Draft the spec — invoke `spec-writer`.** You never write the draft yourself. Assemble the brief per the Sub-agent invocation contract (absolute paths; the sub-agent shares no history) with all of:

   - the spec template below, quoted verbatim;
   - the invoker's **acceptance criteria** and **constraints**, verbatim;
   - the **dropped scope** items from scope confirmation, verbatim (or "None.");
   - **architecture context**: the target `${UNIT}`, interface, and constraints confirmed in step 4, plus the absolute paths of the subsystem doc(s) step 4 found relevant — the spec-writer reads those and only those;
   - `<slug>`, the date, and the absolute path of `<spec>` — the one file the agent writes;
   - when `<supersedes>` is set: the superseded spec's absolute path, with the instruction to include the **Supersedes** header and **Supersession rationale** section.

   The spec-writer fills each template section per the prose rules in `.claude/agents/conventions/specs.md`, which it loads itself.

   ```markdown
   # <Unit> — SPEC

   **Slug:** `<slug>`
   **Date:** `<YYYY-MM-DD>`
   **Supersedes:** `<original-path>`

   ## Purpose
   One paragraph: what this unit does and why it exists.

   ## Interface contract
   Every exported type, interface, error value, and function/method signature the implementer must produce. Doc comment on each.

   ## Behavior
   Numbered rules. Each rule is testable in isolation and names the function or method it constrains.

   ## Test strategy
   Per behavior rule, mark **unit** (no live external services, fakes injected) or **integration** (needs real infrastructure). If any rule is integration-only, state how those tests are gated per `${INTEGRATION_GATE}` in `.claude/project.md`. List the fakes the test-writer should construct for unit tests.

   ## Out of scope
   Bulleted list. Anything a reviewer might reasonably expect this feature to cover but that it does not. Prepopulate with the invoker's **dropped scope** (items the user narrowed out before Phase 1) so the receipt for that decision lives in the spec.

   ## External dependencies
   Every new dependency this feature requires, one per line in the form `name@version — license`. Each license must appear in the allowlist in `.claude/agents/_conventions.md`. Write "None." if the feature adds no dependencies.

   ## Design rationale
   Short prose justifying non-obvious architecture choices — interface boundaries drawn, ports-and-adapters splits, payload shape, anything a future reader would otherwise re-derive. Behavior-neutral. Load-bearing rules belong in Behavior.

   ## Supersession rationale
   Required only when **Supersedes** is set. Justify this design against the superseded spec — what changed and why. State explicitly whether any merged public API changes in a breaking way: flag each breaking change, or assert "No breaking changes to merged public APIs."

   ## Open questions
   Bulleted list, or "None." Each must be resolved before proceeding.
   ```

7. If **Open questions** is non-empty, ask the human, then re-invoke `spec-writer` in revise mode with the questions and answers quoted verbatim — it folds the answers in and removes the section.
8. **Prelint the spec.** Run these deterministic structural checks against `<spec>` yourself. If any fails, re-invoke `spec-writer` in revise mode with the failing checks quoted verbatim, then re-run prelint — do not commit a spec that fails prelint. Cap 3 revise rounds, then escalate. spec-reviewer's heavyweight evaluation comes in Phase 2 and should not be burned on issues this prelint can catch.
   - Required section headers present: `## Purpose`, `## Interface contract`, `## Behavior`, `## Test strategy`, `## Out of scope`, `## External dependencies`, `## Design rationale`, `## Open questions` (unless removed per step 7). When `<supersedes>` is set, `## Supersession rationale` is also required.
   - Every section body is non-empty. The literal `None.` is allowed only in **Out of scope**, **External dependencies**, and **Open questions**.
   - Each **External dependencies** entry matches `name@version — license` (em dash), or the section body is `None.`.
   - **Open questions** is either `None.` or the section was removed in step 7.
9. **Update the registry.** Add a row to `docs/specs/README.md` for `<spec>` with status `active` (create from template if missing). If `<supersedes>` is set, mark the prior row `superseded` linking to `<spec>`.

**Exit gate:** `<spec>` passes prelint, all sections populated, Open questions resolved. Registry has an `active` row for `<spec>` (and a `superseded` row for the prior, in supersede mode).

`git add docs/specs && git commit -m "spec(<slug>): add spec"` (supersede mode: `"spec(<slug>): supersede prior spec"`).
