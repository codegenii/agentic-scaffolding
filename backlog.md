# Backlog

Work queued for later: prompts adjusted to the workflow and ready to run, plus
follow-ups split out of them. Delete an entry when it lands. Template-dev only —
never installed downstream.

## Follow-ups

The `run-journal` feature landed here on 2026-07-19 (spec:
`docs/specs/2026-07-19-run-journal.md`; db-location reasoning:
`docs/decisions.md` §5). These are its open ends.

- `run-journal-integration` — chore in a downstream project, once
  `run-journal-distribution` puts the module there: wrap each agent entry
  point with the decorator, observe-only, no pipeline restructuring. Show the
  diff for one agent and get approval before applying to the rest (a chore
  keeps the human in the loop; the feature workflow does not). Includes
  wiring real `tokens_in` / `tokens_out` / `cost_usd` from whatever the
  pipeline's LLM client exposes; columns stay NULL until then.
- Merging run-journal histories that diverged on parallel machines — out of
  scope until it actually happens (integer run ids collide). `snapshot` /
  `stats --db` cover backup and moving work to another machine.
- `run-journal-workflow-hooks` — the template's own workflow never writes to
  the journal, so per-agent / per-version metrics stay empty in this repo.
  Record each worker-agent run automatically (hook on subagent completion, or
  a driver step in the phases): agent, task/phase, outcome, duration; tokens
  and cost when the harness exposes them. Observe-only — no phase logic
  changes. Distinct from `run-journal-integration` above, which covers a
  downstream pipeline's own agents.
- `run-journal-distribution` — the journal lives in this template repo, but
  installs never carry it: `run_journal.py`, `tests/test_run_journal.py`, and
  `scripts/init-run-journal.sh` are absent from
  `scripts/template-manifest.txt`. Decide how downstream projects get it —
  ship the files via the manifest, or keep the template's copy as reference
  for a per-project re-implementation — then align docs with the choice.
- `run-journal-version-fallback` — repos without `.claude/template-version`
  (this template repo itself included) record NULL and lump under `—` in
  `stats --by-version`. Either resolve the checkout's own HEAD commit by
  reading `.git/HEAD` / refs directly (no shelling out — an existing module
  constraint), or reject the idea and document exporting
  `RUN_JOURNAL_TEMPLATE_VERSION` per machine instead.
- `run-journal-upkeep` — deferred until the journal actually accumulates
  data: a `prune` subcommand (drop runs and their events before a date,
  reclaim space) and a read surface for `log_event` rows (per-run timeline —
  nothing reads `events` today).
- `run-journal-retro-metrics` — deferred until the journal has real data
  (needs `run-journal-workflow-hooks`): record each `/retro` run in the
  journal (window examined, signals found, fixes applied), and consider
  threshold rules for step 2f (auto-flag success% / p95 regressions) once
  there is enough volume to calibrate against.
