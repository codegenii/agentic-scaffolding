# Improvement backlog — template development only

Deferred structural improvements, each as a self-contained prompt to run in a fresh session against this repo. Not part of the template: `/init-project` deletes this file.

## 1. Merge the reviewer conventions files

> `.claude/agents/_conventions.md` (~320 words) and `_conventions-reference.md` (~290 words) are both loaded by spec-reviewer (baseline + Specs detail), splitting one audience's rules across two files. Evaluate merging them into a single reviewer conventions file with an "always" section and an "on demand" section, updating references in `spec-reviewer.md`, `pr-reviewer.md`, `orchestrator/phases/phase-1.md`, and `commands/new-chore.md` (which points at the reference file's Commit messages section — keep that reachable). Keep implementer/test-writer loading unchanged. Verify no agent loads more text than before the merge.

## 2. Structured completion reports for implementer and test-writer

> spec-reviewer and pr-reviewer emit fixed verdict blocks; implementer and test-writer report free-form, constrained only by `_task-preamble.md`'s terse-report rule (verdict/result, files touched, pass/fail evidence). Formalize that rule into a short fixed output schema per agent (e.g. mode, files touched, build/test command + exit status, blockers) in their agent definitions, and update the Phase 4–7 exit-gate text to consume it. Goal: deterministic parsing by the driver and shorter worker outputs; also makes driver-model downgrades (#7) safer to judge.

## 3. Scope the resume-feature test run

> `commands/resume-feature.md` Step 3 runs `${TEST_CMD}` (whole suite) to detect the phase. When the target unit is derivable from the branch's commits (`git log --stat main..HEAD`), run `${TEST_SCOPE_CMD}` instead and fall back to the full suite only if derivation is ambiguous. Cuts resume time on large repos.

## 4. Reduce Phase 7 toolchain re-runs

> Phase 6 exits green (tests + lint), then pr-reviewer re-runs build, lint, and the full test suite. (Phase 7 already has an idempotency guard that skips re-invoking the reviewer when the latest review targets HEAD — this item is about the toolchain cost inside a fresh review.) Evaluate passing Phase 6's evidence (commands run, exit codes, HEAD SHA) in the brief and having pr-reviewer re-run only `${TEST_CMD}` when HEAD matches the evidence SHA. Note from rps-arena: in 2 of 6 PRs the reviewer could not run integration tests at all (no container runtime) and said so in the review — the evidence-passing design should let the reviewer report "verified via Phase 6 evidence" distinctly from "ran it myself". Weigh against reviewer independence — keep the full re-run if the SHA differs or evidence is absent.

## 5. Split pr-reviewer's mechanical checks out (model bump NOT needed)

> Evidence from rps-arena (6 features, 6 PRs): the haiku pr-reviewer produced substantive rule-by-rule reviews with real advisory findings and no attributable missed defects — keep `model: haiku`. The remaining improvement is cost/robustness, not capability: split license classification into a script the driver runs and surface-drift extraction into a deterministic diff step, so the reviewer's context shrinks and the mechanical parts can't be flubbed. Re-evaluate the model only if a downstream project's review evidence shows misses.

## 6. Delegate Phase 1 spec drafting to an opus spec-writer agent

> Today the driver session writes the spec itself in Phase 1, so spec quality depends on whatever model the user happens to drive with. Evidence from rps-arena: the opus spec-reviewer requested changes on 4 of 6 specs — drafting quality is the binding constraint, and each revision round costs a full opus review plus a driver revision turn. Add a `spec-writer` leaf agent (`model: opus`) invoked by Phase 1 step 6 with the template, acceptance criteria, constraints, dropped scope, and architecture context in the brief; the driver keeps prelint, registry, and commits. Update `orchestrator.md`'s agent list and Task-call contract, `new-feature.md`, `_conventions.md`'s loading note, and CONTRIBUTING's Models bullet. Measure: spec-review revision rounds per feature should stay at or below the current 4-in-6 baseline.

## 7. Drive feature sessions on a cheaper model (after #6)

> The driver session is the largest token bucket — its full context re-enters on every turn across all 8 phases. The state machine is deliberately mechanical (objective gates, verbatim extraction, fixed commands), which suits a small model, but two constraints apply: spec drafting must first move to an opus leaf agent (#6), and haiku's 200K context risks mid-feature compaction on large features (sonnet's 1M does not). CONTRIBUTING's Models bullet already recommends a sonnet driver on analysis alone — this experiment confirms or amends it with data. Run one full feature with the session on sonnet, then one on haiku; compare gate compliance (any skipped/misordered phase, wrong commit messages), escalation quality, and peak context size against an opus-driven baseline.

## 8. Repo-wide markdownlint pass + config

> Phases 4–7 and `orchestrator.md`'s worker brief template are markdownlint-clean in their brief content (2026-07-11); the rest of the template still carries the original violations: bare `<placeholder>` tokens in phase 1's spec template (MD033), unlanguaged fences in CONTRIBUTING and bootstrap-guide (MD040), compact table pipes repo-wide (MD060), and missing blank lines around lists/headings in several files (including the phase files' entry/exit gates). Sweep all markdown to those conventions and add a `.markdownlint.jsonc` recording the chosen rule set and table style. The `## Extracted ...` headings the worker brief template emits are a load-bearing contract the agents match on — never rename them. Content-neutral: no wording changes, only formatting.
