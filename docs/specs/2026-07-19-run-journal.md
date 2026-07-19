# run_journal — SPEC

**Slug:** `run-journal`
**Date:** `2026-07-19`

## Purpose

`run_journal` is a single-file Python module (`run_journal.py` at the repo
root) that records agent-run outcomes into one machine-local SQLite journal.
The database lives at the path in `RUN_JOURNAL_DB` (default
`~/.agent-journal/runs.db`), outside any checkout, so every worktree and fork
on a machine appends to one shared history. The module offers three explicit
calls (`start_run`, `log_event`, `finish_run`), a `record` wrapper usable as
both a context manager and a decorator, and a `stats` CLI (`python -m
run_journal stats`) that prints plain-text summaries. Journaling is
best-effort: any storage failure is swallowed and warned so instrumentation
never changes a caller's behavior. It exists to give the workflow a durable,
queryable record of run counts, durations, token usage, cost, and failures
without a server, ORM, or third-party dependency.

## Interface contract

The module is stdlib-only (`sqlite3`, `json`, `os`, `sys`, `datetime`,
`contextlib`, `warnings`, `argparse`). The public surface is top-level
functions only; every other top-level `def` and any class is
underscore-prefixed and is not part of this contract.

### Constants and configuration

- Database path resolution: `RUN_JOURNAL_DB` if set; otherwise
  `~/.agent-journal/runs.db` with `~` user-expanded. The parent directory is
  created if absent.
- `busy_timeout` set on every connection: `5000` milliseconds.
- Percentiles reported by `stats`: the 50th and 95th, computed by nearest-rank
  (sort finished `duration_ms` ascending; rank = `ceil(p/100 * N)`, 1-indexed,
  clamped to `[1, N]`).
- `stats --last` default: `10`.
- Statuses: `running` (set by `start_run`), `success` and `failed` (set by
  `finish_run`).
- Timestamps (`started_at`, `finished_at`, `events.ts`): current UTC ISO-8601
  strings.
- `duration_ms`: non-negative integer milliseconds from the row's `started_at`
  to the current time, computed in `finish_run`.
- Aggregate semantics used by `stats` (per agent, over rows matching the
  optional `--project` filter): success rate = `success / (success + failed)`
  over finished runs; p50/p95 over finished runs' `duration_ms`; total tokens =
  `sum(tokens_in) + sum(tokens_out)` counting NULL as 0; total cost =
  `sum(cost_usd)` counting NULL as 0. "Finished" means status `success` or
  `failed`. When an agent has zero finished runs (its rows are all `running`),
  the agent still gets a per-agent row with its run count, and success rate,
  p50, and p95 are displayed as `—` (em dash); total tokens and total cost still
  sum whatever values are present.

### Schema (created on first use with `CREATE TABLE IF NOT EXISTS`)

```sql
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY,
    project     TEXT NOT NULL,
    agent       TEXT NOT NULL,
    task        TEXT NOT NULL,
    status      TEXT NOT NULL,          -- 'running' | 'success' | 'failed'
    started_at  TEXT NOT NULL,          -- UTC ISO-8601
    finished_at TEXT,                   -- UTC ISO-8601, NULL until finished
    duration_ms INTEGER,                -- NULL until finished
    tokens_in   INTEGER,                -- nullable
    tokens_out  INTEGER,                -- nullable
    cost_usd    REAL,                   -- nullable
    error       TEXT,                   -- nullable
    metadata    TEXT                    -- JSON, nullable
);

CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY,
    run_id  INTEGER NOT NULL,           -- references runs.id
    ts      TEXT NOT NULL,              -- UTC ISO-8601
    type    TEXT NOT NULL,
    payload TEXT                        -- JSON, nullable
);
```

### Public functions

```python
def start_run(agent, task, metadata=None):
    """Insert a 'running' run row and return its integer id, or None on failure.

    Records `agent`, `task`, `started_at` (current UTC ISO-8601), status
    'running', `metadata` serialized as JSON, and a resolved `project`:
    `RUN_JOURNAL_PROJECT` if set, else the repo-name derived by walking up from
    the working directory to the nearest `.git` entry (see Behavior). Returns
    the new row's id (int). On any journal failure emits one warning and
    returns None; never raises.
    """

def log_event(run_id, event_type, payload=None):
    """Append one row to `events`: (run_id, ts, event_type, payload).

    `ts` is the current UTC ISO-8601 string; `payload` is serialized as JSON and
    stored in the `type`-adjacent `payload` column. `event_type` is stored in
    the `events.type` column. Events are optional — callers may omit them
    entirely. Returns None; on any journal failure emits one warning and returns
    None without raising.
    """

def finish_run(run_id, status, tokens_in=None, tokens_out=None, cost=None,
               error=None):
    """Close a run: set status, finished_at, and computed duration_ms.

    `status` is 'success' or 'failed'. `finished_at` is the current UTC ISO-8601
    string; `duration_ms` is the non-negative integer milliseconds from the
    row's stored `started_at` to now. `tokens_in`, `tokens_out`, `cost`
    (stored in `cost_usd`), and `error` are written when provided and left as
    SQL NULL when None. Returns None; on any journal failure (including an
    unknown or None `run_id`) emits one warning and returns None without raising.
    """

@contextlib.contextmanager
def record(agent, task, metadata=None):
    """Journal a wrapped call; usable as a context manager and as a decorator.

    On entry calls `start_run(agent, task, metadata)` and yields the run_id (or
    None if that failed). On normal completion calls
    `finish_run(run_id, 'success')`. If the wrapped body raises, calls
    `finish_run(run_id, 'failed', error=str(exc))` and re-raises the original
    exception unchanged. Journal failures inside start_run/finish_run are
    swallowed and warned; only the wrapped callable's exception propagates.
    Usable as `with record(...) as run_id:` and as `@record(...)`.
    """

def main(argv=None):
    """CLI entry for `python -m run_journal`. Returns a process exit code (int).

    Parses `argv` (default `sys.argv[1:]`). The `stats` subcommand prints
    plain-text tables to stdout: a per-agent table (run count, success rate,
    p50/p95 duration_ms, total tokens, total cost), the last N runs
    (`--last N`, default 10; status and duration), and failed runs with their
    error messages. `--project NAME` filters all three sections. Returns 0 on
    success; on a journal read failure emits one warning and returns a non-zero
    code without raising. Unrecognized or missing subcommands print usage and
    return a non-zero code.
    """
```

There are no exported error types: journal failures are never surfaced to
callers (see Behavior). The module reads no third-party import.

## Behavior

Path and schema:

1. `start_run`, `log_event`, `finish_run`, and `main` each resolve the database
   path from `RUN_JOURNAL_DB`, falling back to a user-expanded
   `~/.agent-journal/runs.db` when the variable is unset, creating the parent
   directory if it does not exist.
2. On first use against a fresh path, the first public call creates the `runs`
   and `events` tables with the columns in the Interface contract.
3. After any public call completes, the database is in WAL mode (a fresh
   connection reports `PRAGMA journal_mode` = `wal`). Each connection is
   short-lived (open, transact, close) and sets `busy_timeout` to 5000 ms.

`start_run`:

4. `start_run(agent, task, metadata)` inserts exactly one row with status
   `running`, the given `agent` and `task`, `started_at` set to the current UTC
   ISO-8601 string, `metadata` serialized as JSON, and returns the new row's
   integer id.
5. When `RUN_JOURNAL_PROJECT` is set, `start_run` stores that value as the
   row's `project`.
6. When `RUN_JOURNAL_PROJECT` is unset, `start_run` derives `project` by walking
   up from the working directory to the nearest `.git` entry: if `.git` is a
   directory, `project` is the basename of its parent directory; if `.git` is a
   file, `project` is the basename of the main checkout parsed from the file's
   `gitdir:` line (`<main-checkout>/.git/worktrees/<name>`); if no `.git`
   ancestor exists, `project` is the basename of the working directory. It does
   not invoke `git`.

`log_event`:

7. `log_event(run_id, event_type, payload)` appends exactly one row to `events`
   with the given `run_id`, `ts` set to the current UTC ISO-8601 string,
   `event_type` in the `type` column, and `payload` serialized as JSON.

`finish_run`:

8. `finish_run(run_id, status, ...)` updates that run's `status`, sets
   `finished_at` to the current UTC ISO-8601 string, and sets `duration_ms` to
   the non-negative integer milliseconds between the row's stored `started_at`
   and now.
9. `finish_run` writes `tokens_in`, `tokens_out`, `cost` (into `cost_usd`), and
   `error` when each is provided, and leaves any argument passed as None as SQL
   NULL.

`record` wrapper:

10. `record(agent, task, metadata)` used as a context manager calls `start_run`
    on entry, yields the resulting run_id, and calls
    `finish_run(run_id, 'success')` on normal block exit.
11. `record(agent, task, metadata)` used as a decorator wraps a function so that
    each invocation records a run with the same start/finish semantics as rule
    10, and the wrapped function's return value is returned to the caller
    unchanged.
12. When the body wrapped by `record` raises, `record` calls
    `finish_run(run_id, 'failed', error=str(exc))` and then re-raises the
    original exception object unchanged.
13. Rule 12 holds even when the wrapped-run journaling fails: a journal error
    inside `record`'s own `start_run`/`finish_run` is swallowed and warned, but
    the wrapped callable's exception still propagates.

Journal-failure policy:

14. When a journal operation fails — unwritable or invalid db path, locked
    database, non-JSON-serializable `metadata` or `payload`, or a disk error —
    `start_run` returns None and `log_event`/`finish_run` return None; each
    emits exactly one warning and none raises.

Concurrency:

15. Two writers (separate processes or threads) each calling `start_run` /
    `finish_run` concurrently against the same database both commit their rows;
    neither loses its write to a "database is locked" error (WAL +
    `busy_timeout`).

`stats` CLI:

16. `main(['stats'])` prints a per-agent table whose columns are run count,
    success rate, p50 `duration_ms`, p95 `duration_ms`, total tokens, and total
    cost, computed with the aggregate semantics in the Interface contract. An
    agent whose runs are all `running` (zero finished runs) still gets a row:
    its run count is shown, success rate, p50, and p95 are shown as `—` (em
    dash), and total tokens and total cost still sum any present values.
17. `main(['stats', '--last', 'N'])` prints the most recent N runs ordered by
    `started_at` descending, each showing status and duration; N defaults to 10
    when `--last` is omitted.
18. `main(['stats'])` prints a failures section listing runs with status
    `failed`, each with its `error` message.
19. `main(['stats', '--project', 'NAME'])` restricts all three sections to runs
    whose `project` equals `NAME`.
20. `main` returns 0 on a successful `stats` run; on a journal read failure it
    emits one warning and returns a non-zero exit code without raising.
21. When no runs match, `main(['stats'])` returns 0 and prints the section
    headers (or empty-table placeholders) rather than raising or erroring.

## Test strategy

`${INTEGRATION_GATE}` is `none` — there is no integration tier. Every rule
below is a **unit** test run by `${TEST_CMD}`
(`python -m unittest discover -s tests -t .`); no rule needs live external
infrastructure, because the module touches only a local SQLite file and process
environment. No gating is required.

| Rule | Kind | Notes |
|---|---|---|
| 1 | unit | Set `RUN_JOURNAL_DB` to a temp path; assert the file and parent dir are created. |
| 2 | unit | Fresh temp path; after `start_run`, query `sqlite_master` for both tables. |
| 3 | unit | After a public call, open a fresh connection and assert `PRAGMA journal_mode` = `wal`. |
| 4 | unit | Assert the inserted row's columns and returned int id. |
| 5 | unit | Set `RUN_JOURNAL_PROJECT`; read back the stored `project`. |
| 6 | unit | Temp-dir fixtures: a `.git` directory, a `.git` file with a `gitdir:` worktree line, and no `.git` ancestor; unset `RUN_JOURNAL_PROJECT`; assert derived project. |
| 7 | unit | Assert the appended `events` row's columns. |
| 8 | unit | Assert `status`, `finished_at`, and a non-negative `duration_ms`. |
| 9 | unit | Provide some fields and omit others; assert written values and NULLs. |
| 10 | unit | `with record(...) as rid:`; assert a `success` row. |
| 11 | unit | Apply `@record(...)` to a function; call it; assert return value and a `success` row. |
| 12 | unit | Wrap a callable that raises; assert the exception propagates and a `failed` row with the message. |
| 13 | unit | Force a journal error while wrapping a raising callable; assert the callable's exception still propagates. |
| 14 | unit | Point `RUN_JOURNAL_DB` at an unwritable/invalid path and pass a non-serializable payload; assert None returns, one warning, no raise. |
| 15 | unit | Two threads (or subprocesses) write concurrently; assert both rows commit. |
| 16-21 | unit | Seed the temp db with rows, capture stdout, and assert table content, ordering, `--last`/`--project` filtering, exit codes, the empty-journal case, and a per-agent row whose runs are all `running` (rate/p50/p95 shown as `—`). |

Fakes and fixtures the test-writer constructs (no external-service fakes are
needed):

- A temp database file via `tempfile`, with `RUN_JOURNAL_DB` pointed at it in
  `setUp`/`tearDown` (per the machine-state invariant, tests never touch the
  default path).
- Temp-directory fixtures for the project-name walk: a directory containing a
  `.git` directory; a directory containing a `.git` file whose contents are
  `gitdir: <path>/.git/worktrees/<name>`; and a directory with no `.git`
  ancestor. Control the working directory (`os.chdir` with restore, or a
  cwd-injection seam) and the `RUN_JOURNAL_PROJECT` / `RUN_JOURNAL_DB` env vars.
- An invalid db path (e.g., a path whose parent is a regular file) or a
  monkeypatched connection helper to force journal failures for rules 13-14 and
  20.
- A callable that raises a known exception type for the wrapper tests.
- Warning capture via `warnings.catch_warnings(record=True)` (or stderr
  capture) and stdout capture for the CLI tests.
- Two-writer concurrency exercised with `threading` or `subprocess` against one
  shared temp db.

## Out of scope

- Dropped scope from the invoker: None — no items were narrowed out before
  Phase 1.
- Rollout to agent entry points: wiring `run_journal` into existing pipeline
  files is a separate chore. This feature adds only `run_journal.py` and
  `tests/test_run_journal.py` and touches no existing pipeline file.
- Managing `.gitignore`: the module does not create or edit ignore rules. The
  feature branch is expected to add `runs.db`, `runs.db-wal`, and `runs.db-shm`
  to the repo `.gitignore` as a safety net for non-default (in-checkout)
  `RUN_JOURNAL_DB` paths, but that is a repo-config change, not module behavior,
  and no behavior rule covers it.
- Automatic token/cost measurement: the `record` wrapper records only
  success/failure and duration. Token and cost figures are supplied by callers
  through `finish_run`; the wrapper leaves them NULL.
- Servers, Docker, queues, background daemons, and any web UI: the module is a
  library plus a synchronous CLI over one local file.
- An ORM or query builder: storage is hand-written SQL over stdlib `sqlite3`.
- A programmatic read/query API: reading is available only through the `stats`
  CLI; no exported functions return rows or aggregates.
- Output formats other than plain-text tables (no JSON/CSV export) and
  configurable percentile sets beyond p50/p95.
- Retention, rotation, pruning, or archival of old runs and events; the journal
  grows unbounded.
- Schema migrations: the schema is created once with `CREATE TABLE IF NOT
  EXISTS`; evolving existing columns is not handled.

## External dependencies

None.

## Design rationale

- **Functions-only public surface.** The project's surface-drift check matches
  top-level `def` and cannot see classes (`.claude/project.md`,
  `${EXPORT_PATTERN}`), so the API is exported as top-level functions; the
  dual-use `record` is a `contextlib.contextmanager` generator, which yields an
  object usable as both `with` and `@` (`ContextDecorator`), avoiding a
  public class. Internal helpers and any internal class are underscore-prefixed.
- **Short-lived connection per call + WAL + busy_timeout.** Each public call
  opens, transacts, and closes its own connection with
  `PRAGMA journal_mode=WAL` and a 5000 ms `busy_timeout`. WAL lets a reader and
  a writer proceed without blocking each other, and the busy_timeout makes a
  second concurrent writer wait for the lock rather than fail immediately; this
  is what lets two writer processes both commit (per the brief's concurrency
  stance). No connection pool or long-lived handle is kept, which keeps the
  module reentrant across processes that share one file.
- **Swallow-and-warn boundary.** Journaling is instrumentation, so a storage
  fault must not change a caller's outcome. Every public function catches
  `Exception` at its boundary, emits one warning, and returns a null-ish value.
  The `record` wrapper is the one place two failure domains meet: it isolates
  its own journal errors (swallowed) from the wrapped callable's exception
  (always re-raised), so instrumentation is transparent to the wrapped code.
- **Project name without invoking git.** Resolving `project` by reading `.git`
  directory-vs-file and parsing the `gitdir:` line (per the brief's
  architecture context) keeps every worktree of one repo under a single
  project name with no subprocess, which matters because the journal is shared
  across all worktrees on the machine.
- **UTC ISO-8601 strings; duration computed on close.** Timestamps are stored
  as text for portability and human-readable inspection; `duration_ms` is
  derived in `finish_run` from the stored `started_at`, so a run's duration is
  authoritative from its own recorded start rather than a caller-passed value.

## Open questions

None.
