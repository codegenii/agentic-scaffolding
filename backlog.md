# Improvement backlog — template development only

Deferred structural improvements, each as a self-contained prompt to run in a fresh session against this repo. Not part of the template: `/init-project` deletes this file.

## 1. Merge the reviewer conventions files

> `.claude/agents/_conventions.md` and `_conventions-reference.md` are both loaded by spec-reviewer (baseline + Specs detail), splitting one audience's rules across two files. Evaluate merging them into a single reviewer conventions file with an "always" section and an "on demand" section, updating references in `spec-reviewer.md`, `pr-reviewer.md`, `orchestrator/phases/phase-1.md`, and `commands/new-chore.md`. Keep implementer/test-writer loading unchanged. Verify no file loads more text than before the merge.

## 2. Factor the shared brief scaffold out of phase files

> Phases 4–7 in `.claude/orchestrator/phases/` each repeat the same brief skeleton: the "Spec path (reference only — do not read)" line, the context-card line, and the `## Extracted <Section>` blocks. Extract a single brief template (e.g. in `orchestrator.md`) that each phase fills with its agent, instruction, and section list, so each phase file states only what is unique to it. Preserve exact brief semantics — the workers' behavior must not change.

## 3. Structured completion reports for implementer and test-writer

> spec-reviewer and pr-reviewer emit fixed verdict blocks; implementer and test-writer report free-form. Define a short fixed output schema for each (e.g. mode, files touched, build/test command + exit status, blockers) in their agent definitions, and update the Phase 4–7 exit-gate text to consume it. Goal: deterministic parsing by the driver and shorter worker outputs.

## 4. Scope the resume-feature test run

> `commands/resume-feature.md` Step 3 runs `${TEST_CMD}` (whole suite) to detect the phase. When the target unit is derivable from the branch's commits (`git log --stat main..HEAD`), run `${TEST_SCOPE_CMD}` instead and fall back to the full suite only if derivation is ambiguous. Cuts resume time on large repos.

## 5. Reduce Phase 7 toolchain re-runs

> Phase 6 exits green (tests + lint), then pr-reviewer immediately re-runs build, lint, and the full test suite. Evaluate passing Phase 6's evidence (commands run, exit codes, HEAD SHA) in the brief and having pr-reviewer re-run only `${TEST_CMD}` when HEAD matches the evidence SHA. Weigh against reviewer independence — keep the full re-run if the SHA differs or evidence is absent.

## 6. Fit pr-reviewer's checklist to its model

> `pr-reviewer` runs on `haiku` but carries the widest checklist (toolchain, five finding sections, license resolution, surface-drift diffing). Either upgrade the model for review-critical projects, or split the mechanical parts out: license classification as a script the driver runs, surface-drift extraction as a deterministic step. Decide per project via a `${...}` variable in `project.md` if both options should stay available.
