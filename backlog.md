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

- One new single-file module `run_journal` owning one SQLite database
  `runs.db`, opened in WAL mode with a busy_timeout; schema created on first
  use:
  - runs(id, agent, task, status running|success|failed, started_at,
    finished_at, duration_ms, tokens_in, tokens_out, cost_usd, error,
    metadata JSON)
  - events(id, run_id, ts, type, payload JSON)
- start_run(agent, task, metadata) -> run_id inserts a running row.
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
- No servers, Docker, queues, or web UI. One database file; gitignore runs.db.
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

## Follow-ups

- `run-journal-integration` — chore in the downstream project, after
  `run-journal` merges: wrap each agent entry point with the decorator,
  observe-only, no pipeline restructuring. Show the diff for one agent and get
  approval before applying to the rest (a chore keeps the human in the loop;
  the feature workflow does not). Includes wiring real `tokens_in` /
  `tokens_out` / `cost_usd` from whatever the pipeline's LLM client exposes;
  columns stay NULL until then.
