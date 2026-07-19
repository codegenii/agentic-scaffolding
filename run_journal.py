"""Run journal: stdlib-only SQLite-backed logging for agent run telemetry.

Configuration is read from the environment at call time: `RUN_JOURNAL_DB`
(journal database path, default `~/.agent-journal/runs.db`) and
`RUN_JOURNAL_PROJECT` (overrides the derived project name).
"""

import contextlib


def start_run(agent, task, metadata=None):
    """Insert a 'running' run row and return its integer id, or None on failure.

    Records `agent`, `task`, `started_at` (current UTC ISO-8601), status
    'running', `metadata` serialized as JSON, and a resolved `project`:
    `RUN_JOURNAL_PROJECT` if set, else the repo-name derived by walking up from
    the working directory to the nearest `.git` entry (see Behavior). Returns
    the new row's id (int). On any journal failure emits one warning and
    returns None; never raises.
    """
    raise NotImplementedError("not implemented")


def log_event(run_id, event_type, payload=None):
    """Append one row to `events`: (run_id, ts, event_type, payload).

    `ts` is the current UTC ISO-8601 string; `payload` is serialized as JSON and
    stored in the `type`-adjacent `payload` column. `event_type` is stored in
    the `events.type` column. Events are optional — callers may omit them
    entirely. Returns None; on any journal failure emits one warning and
    returns None without raising.
    """
    raise NotImplementedError("not implemented")


def finish_run(run_id, status, tokens_in=None, tokens_out=None, cost=None,
               error=None):
    """Close a run: set status, finished_at, and computed duration_ms.

    `status` is 'success' or 'failed'. `finished_at` is the current UTC
    ISO-8601 string; `duration_ms` is the non-negative integer milliseconds
    from the row's stored `started_at` to now. `tokens_in`, `tokens_out`,
    `cost` (stored in `cost_usd`), and `error` are written when provided and
    left as SQL NULL when None. Returns None; on any journal failure
    (including an unknown or None `run_id`) emits one warning and returns None
    without raising.
    """
    raise NotImplementedError("not implemented")


@contextlib.contextmanager
def record(agent, task, metadata=None):
    """Journal a wrapped call; usable as a context manager and as a decorator.

    On entry calls `start_run(agent, task, metadata)` and yields the run_id
    (or None if that failed). On normal completion calls
    `finish_run(run_id, 'success')`. If the wrapped body raises, calls
    `finish_run(run_id, 'failed', error=str(exc))` and re-raises the original
    exception unchanged. Journal failures inside start_run/finish_run are
    swallowed and warned; only the wrapped callable's exception propagates.
    Usable as `with record(...) as run_id:` and as `@record(...)`.
    """
    raise NotImplementedError("not implemented")
    yield


def main(argv=None):
    """CLI entry for `python -m run_journal`. Returns a process exit code (int).

    Parses `argv` (default `sys.argv[1:]`). The `stats` subcommand prints
    plain-text tables to stdout: a per-agent table (run count, success rate,
    p50/p95 duration_ms, total tokens, total cost), the last N runs
    (`--last N`, default 10; status and duration), and failed runs with their
    error messages. `--project NAME` filters all three sections. Returns 0 on
    success; on a journal read failure emits one warning and returns a
    non-zero code without raising. Unrecognized or missing subcommands print
    usage and return a non-zero code.
    """
    raise NotImplementedError("not implemented")
