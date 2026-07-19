# Spec registry

Every feature spec lives in this directory as `<YYYY-MM-DD>-<slug>.md`. A **feature spec** is the design document for one unit of work, written and approved before any code (see `.claude/orchestrator.md`, Phases 1–2).

A spec's **behavior is immutable once approved.** Changing what a feature does — adding, removing, or altering a behavior rule or an interface's semantics — is never an edit. It is a new dated spec that supersedes the old one. The orchestrator's supersede mode writes the new spec and updates the rows below.

**Editorial changes are made in place.** A behavior-neutral change — renaming a symbol, clarifying prose, fixing a typo — needs no supersede: edit the approved spec directly. The test for "editorial": the implementation and tests still satisfy the spec unchanged, or change only by the same mechanical rename. Anything that alters behavior supersedes instead.

This table is the index of every spec and its status. `Status` is `active`, or `superseded` linking to the spec that replaced it.

| Date | Spec | Status | Supersedes |
|------|------|--------|------------|
| 2026-07-19 | [2026-07-19-run-journal.md](2026-07-19-run-journal.md) | active | — |
