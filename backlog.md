# Improvement backlog — template development only

Deferred structural improvements, each as a self-contained prompt to run in a fresh session against this repo. Not part of the template: `/init-project` deletes this file.

## 1. Split pr-reviewer's mechanical checks out (model bump NOT needed)

> Evidence from rps-arena (6 features, 6 PRs): the haiku pr-reviewer produced substantive rule-by-rule reviews with real advisory findings and no attributable missed defects — keep `model: haiku`. The remaining improvement is cost/robustness, not capability: split license classification into a script the driver runs and surface-drift extraction into a deterministic diff step, so the reviewer's context shrinks and the mechanical parts can't be flubbed. Re-evaluate the model only if a downstream project's review evidence shows misses.

## 2. Delegate Phase 1 spec drafting to an opus spec-writer agent

> Today the driver session writes the spec itself in Phase 1, so spec quality depends on whatever model the user happens to drive with. Evidence from rps-arena: the opus spec-reviewer requested changes on 4 of 6 specs — drafting quality is the binding constraint, and each revision round costs a full opus review plus a driver revision turn. Add a `spec-writer` leaf agent (`model: opus`) invoked by Phase 1 step 6 with the template, acceptance criteria, constraints, dropped scope, and architecture context in the brief; the driver keeps prelint, registry, and commits. Update `orchestrator.md`'s agent list and Task-call contract, `new-feature.md`, `_conventions.md`'s loading note, and CONTRIBUTING's Models bullet. Measure: spec-review revision rounds per feature should stay at or below the current 4-in-6 baseline.

## 3. Drive feature sessions on a cheaper model (after #2)

> The driver session is the largest token bucket — its full context re-enters on every turn across all 8 phases. The state machine is deliberately mechanical (objective gates, verbatim extraction, fixed commands), which suits a small model, but two constraints apply: spec drafting must first move to an opus leaf agent (#2), and haiku's 200K context risks mid-feature compaction on large features (sonnet's 1M does not). CONTRIBUTING's Models bullet already recommends a sonnet driver on analysis alone — this experiment confirms or amends it with data. Run one full feature with the session on sonnet, then one on haiku; compare gate compliance (any skipped/misordered phase, wrong commit messages), escalation quality, and peak context size against an opus-driven baseline.

## 4. Repo-wide markdownlint pass + config

> Phases 4–7 and `orchestrator.md`'s worker brief template are markdownlint-clean in their brief content (2026-07-11); the rest of the template still carries the original violations: bare `<placeholder>` tokens in phase 1's spec template (MD033), unlanguaged fences in CONTRIBUTING and bootstrap-guide (MD040), compact table pipes repo-wide (MD060), and missing blank lines around lists/headings in several files (including the phase files' entry/exit gates). Sweep all markdown to those conventions and add a `.markdownlint.jsonc` recording the chosen rule set and table style. The `## Extracted ...` headings the worker brief template emits are a load-bearing contract the agents match on — never rename them. Content-neutral: no wording changes, only formatting.
