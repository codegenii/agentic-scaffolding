# Backlog

Work queued for later: prompts adjusted to the workflow and ready to run, plus
follow-ups split out of them. Delete an entry when it lands. Template-dev only —
never installed downstream.

## Ready — run-journal (downstream feature)

SQLite run journal with metrics for an agent pipeline. Run it in a downstream
project that has a pipeline — this template has no runtime code. Feed the block
below to `/new-feature`; adjust module naming to the project's layout.

```text
/new-feature run-journal

Acceptance criteria:

- One new single-file module `run_journal` owning one SQLite database at the
  path in `RUN_JOURNAL_DB` (default `~/.agent-journal/runs.db` — outside any
  checkout, so all worktrees and forks on a machine share one journal),
  opened in WAL mode with a busy_timeout; schema created on first use:
  - runs(id, project, agent, task, status running|success|failed, started_at,
    finished_at, duration_ms, tokens_in, tokens_out, cost_usd, error,
    metadata JSON)
  - events(id, run_id, ts, type, payload JSON)
- start_run(agent, task, metadata) -> run_id inserts a running row; each run
  records a project (env RUN_JOURNAL_PROJECT, else the working directory's
  repo name), and stats can filter by it.
- log_event(run_id, type, payload) appends an event row (callers may skip it).
- finish_run(run_id, status, tokens_in, tokens_out, cost, error) closes the
  run and computes duration_ms.
- A context manager / decorator records a wrapped call automatically: success
  on normal return; on exception, a failed run with the error message, then
  the exception re-raises unchanged.
- Journal failures (locked db, bad payload, disk error) never propagate to
  the caller — swallow and warn. Token/cost fields are nullable.
- Two processes writing concurrently both commit (WAL + busy_timeout).
- A stats command (python -m run_journal stats) prints plain-text tables:
  per-agent run count, success rate, p50/p95 duration, total tokens, total
  cost; the last N runs with status and duration; failures with error
  messages.

Constraints:

- Stdlib only (sqlite3) — External dependencies: None. No ORM.
- No servers, Docker, queues, or web UI. One database file, outside the
  checkout by default (still gitignore runs.db).
- This feature adds the module and its tests only — it must not touch any
  existing pipeline file. Rollout to agent entry points is a separate chore.
- Aim for ~200 source lines (tests excluded); drop niceties before growing.
```

Adjustments from the original prompt:

- Integration rollout ("wrap my existing agent entry points", "show me the
  diff for one agent before applying to all") split into the follow-up chore
  below — the state machine has no mid-feature approval stop (human gates are
  Phase 2 spec approval and Phase 7 PR review), and a feature builds a new
  unit rather than editing files across the pipeline.
- Requirements reworded as testable acceptance criteria — Phase 5 turns them
  into failing tests.
- "No dependencies beyond stdlib" mapped to the spec's `External dependencies:
  None`, which makes Phase 3 a no-op.
- Database moved from a repo-relative `runs.db` to a machine-level default
  (`RUN_JOURNAL_DB`) with a `project` column — a repo-relative file would
  fragment per worktree and die with `prune-worktrees.sh`, and the shared
  path lets all forks on a machine feed one journal.

## Follow-ups

- `run-journal-integration` — chore in the downstream project, after
  `run-journal` merges: wrap each agent entry point with the decorator,
  observe-only, no pipeline restructuring. Show the diff for one agent and get
  approval before applying to the rest (a chore keeps the human in the loop;
  the feature workflow does not). Includes wiring real `tokens_in` /
  `tokens_out` / `cost_usd` from whatever the pipeline's LLM client exposes;
  columns stay NULL until then.
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
- `run-journal-distribution` — installs never carry the journal:
  `run_journal.py`, `tests/test_run_journal.py`, and
  `scripts/init-run-journal.sh` are absent from
  `scripts/template-manifest.txt`, while the "Ready — run-journal" block
  above still tells operators to re-implement the feature downstream via
  `/new-feature`. Pick one path — ship the files via the manifest and delete
  the Ready block, or keep the re-implement flow and mark the template's copy
  as reference — then align backlog and docs.
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
