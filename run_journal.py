"""Run journal: stdlib-only SQLite-backed logging for agent run telemetry.

Configuration is read from the environment at call time: `RUN_JOURNAL_DB`
(journal database path, default `~/.agent-journal/runs.db`),
`RUN_JOURNAL_PROJECT` (overrides the derived project name), and
`RUN_JOURNAL_TEMPLATE_VERSION` (overrides the template version recorded on
each run; default is the `commit` value from the checkout root's
`.claude/template-version`, written by the template installer).

First-run machine setup: `scripts/init-run-journal.sh <absolute-path>`
creates the machine-wide database and fails loudly (journal failures are
otherwise swallowed). Any public call also bootstraps a missing database in
place.

Backup: `python -m run_journal snapshot <dest>` writes a consistent
single-file copy via `VACUUM INTO`; never file-copy a live WAL database.
Restore: copy a snapshot over the journal path, or point `RUN_JOURNAL_DB` at
it (`stats --db <path>` reads one in place). Keep the database on a local
filesystem — WAL is unsafe on network filesystems.
"""

import argparse
import contextlib
import datetime
import json
import os
import sqlite3
import sys
import urllib.parse
import warnings

_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY,
    project     TEXT NOT NULL,
    agent       TEXT NOT NULL,
    task        TEXT NOT NULL,
    status      TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    cost_usd    REAL,
    error       TEXT,
    metadata    TEXT,
    template_version TEXT,
    cache_read_tokens INTEGER,
    cache_creation_tokens INTEGER
)
"""

_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY,
    run_id  INTEGER NOT NULL,
    ts      TEXT NOT NULL,
    type    TEXT NOT NULL,
    payload TEXT
)
"""

_GITDIR_WORKTREE_MARKER = "/.git/worktrees/"
_DEFAULT_LAST_N = 10
_FINISHED_STATUSES = ("success", "failed")

# Paths whose schema has already been created in this process. Avoids
# re-running (idempotent, but not free) CREATE TABLE statements on every
# connection, which otherwise adds needless write-lock contention when
# many callers hit the same database concurrently.
_initialized_paths = set()


# ---------------------------------------------------------------------------
# Path resolution, connection, and schema bootstrap
# ---------------------------------------------------------------------------


def _resolve_db_path():
    path = os.environ.get("RUN_JOURNAL_DB")
    if not path:
        path = os.path.join(os.path.expanduser("~"), ".agent-journal", "runs.db")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


def _connect():
    path = _resolve_db_path()
    conn = sqlite3.connect(path, timeout=5.0)
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        _ensure_wal_and_schema(conn, path)
    except Exception:
        conn.close()
        raise
    return conn


def _connect_readonly(path):
    """Open an existing database file read-only — no create, no WAL switch.

    Used for `stats --db`, so reading a snapshot can never mutate it (or
    conjure an empty database at a mistyped path).
    """
    normalized = os.path.abspath(path).replace(os.sep, "/")
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    uri = "file:" + urllib.parse.quote(normalized, safe="/:") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _ensure_wal_and_schema(conn, path):
    """Switch to WAL and ensure tables exist, retrying past lock contention.

    Switching a fresh (non-WAL) database file to WAL mode requires a
    momentary exclusive lock; when several connections race to do this for
    the first time, SQLite can report "database is locked" without honoring
    `busy_timeout`. Retrying the whole bootstrap a bounded number of times
    lets the losing connections observe the winner's already-applied change
    and proceed, rather than surfacing a spurious journal failure.
    """
    last_exc = None
    for _ in range(500):
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            if path not in _initialized_paths:
                conn.execute(_RUNS_TABLE_SQL)
                conn.execute(_EVENTS_TABLE_SQL)
                _migrate_runs_columns(conn)
                conn.commit()
                _initialized_paths.add(path)
            return
        except sqlite3.OperationalError as exc:
            last_exc = exc
    raise last_exc


# Columns added after the initial schema, in the order they were introduced.
# Fresh databases get them from _RUNS_TABLE_SQL; existing ones via ALTER TABLE.
_ADDED_RUNS_COLUMNS = (
    ("template_version", "TEXT"),
    ("cache_read_tokens", "INTEGER"),
    ("cache_creation_tokens", "INTEGER"),
)


def _migrate_runs_columns(conn):
    """Additive migration for databases created before newer columns existed."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
    for name, sql_type in _ADDED_RUNS_COLUMNS:
        if name in columns:
            continue
        try:
            conn.execute(f"ALTER TABLE runs ADD COLUMN {name} {sql_type}")
        except sqlite3.OperationalError as exc:
            # Lost a race with another process adding the same column.
            if "duplicate column" not in str(exc).lower():
                raise


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_iso_utc(value):
    parsed = datetime.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Project and template-version derivation
# ---------------------------------------------------------------------------


def _resolve_project():
    env_project = os.environ.get("RUN_JOURNAL_PROJECT")
    if env_project:
        return env_project
    return _derive_project_from_git_ancestor(os.getcwd())


def _find_checkout_root(start_dir):
    """Return the nearest ancestor directory holding a `.git` entry, or None."""
    current = os.path.abspath(start_dir)
    while True:
        git_path = os.path.join(current, ".git")
        if os.path.isdir(git_path) or os.path.isfile(git_path):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _derive_project_from_git_ancestor(start_dir):
    root = _find_checkout_root(start_dir)
    if root is None:
        return os.path.basename(os.path.abspath(start_dir))
    git_path = os.path.join(root, ".git")
    if os.path.isfile(git_path):
        return _project_from_gitdir_file(git_path)
    return os.path.basename(root)


def _project_from_gitdir_file(git_file_path):
    with open(git_file_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    gitdir_value = ""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("gitdir:"):
            gitdir_value = line[len("gitdir:"):].strip()
            break
    normalized = gitdir_value.replace("\\", "/")
    index = normalized.find(_GITDIR_WORKTREE_MARKER)
    main_checkout = normalized[:index] if index != -1 else normalized
    return os.path.basename(main_checkout.rstrip("/"))


def _resolve_template_version():
    env_version = os.environ.get("RUN_JOURNAL_TEMPLATE_VERSION")
    if env_version:
        return env_version
    root = _find_checkout_root(os.getcwd())
    if root is None:
        return None
    return _read_template_version_file(
        os.path.join(root, ".claude", "template-version"))


def _read_template_version_file(path):
    """Parse the installer-written file: the `commit <sha>` line's value,
    else the first non-empty line."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = [line.strip() for line in fh.read().splitlines()]
    except OSError:
        return None
    for line in lines:
        if line.startswith("commit "):
            return line[len("commit "):].strip() or None
    for line in lines:
        if line:
            return line
    return None


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def start_run(agent, task, metadata=None):
    """Insert a 'running' run row and return its integer id, or None on failure.

    Records `agent`, `task`, `started_at` (current UTC ISO-8601), status
    'running', `metadata` serialized as JSON, a resolved `project`
    (`RUN_JOURNAL_PROJECT` if set, else the repo-name derived by walking up
    from the working directory to the nearest `.git` entry), and a
    `template_version` (`RUN_JOURNAL_TEMPLATE_VERSION` if set, else the
    `commit` recorded in the checkout root's `.claude/template-version`, else
    NULL). Returns the new row's id (int). On any journal failure emits one
    warning and returns None; never raises.
    """
    try:
        metadata_json = json.dumps(metadata) if metadata is not None else None
        project = _resolve_project()
        template_version = _resolve_template_version()
        started_at = _utc_now().isoformat()
        conn = _connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO runs
                    (project, agent, task, status, started_at, metadata,
                     template_version)
                VALUES (?, ?, ?, 'running', ?, ?, ?)
                """,
                (project, agent, task, started_at, metadata_json,
                 template_version),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
    except Exception as exc:  # any journal failure is swallowed, never raised
        warnings.warn(f"run_journal: start_run failed: {exc}")
        return None


def log_event(run_id, event_type, payload=None):
    """Append one row to `events`: (run_id, ts, event_type, payload).

    `ts` is the current UTC ISO-8601 string; `payload` is serialized as JSON and
    stored in the `type`-adjacent `payload` column. `event_type` is stored in
    the `events.type` column. Events are optional — callers may omit them
    entirely. Returns None; on any journal failure emits one warning and
    returns None without raising.
    """
    try:
        payload_json = json.dumps(payload) if payload is not None else None
        ts = _utc_now().isoformat()
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO events (run_id, ts, type, payload) VALUES (?, ?, ?, ?)",
                (run_id, ts, event_type, payload_json),
            )
            conn.commit()
        finally:
            conn.close()
        return None
    except Exception as exc:  # any journal failure is swallowed, never raised
        warnings.warn(f"run_journal: log_event failed: {exc}")
        return None


def finish_run(run_id, status, tokens_in=None, tokens_out=None, cost=None,
               error=None, cache_read_tokens=None, cache_creation_tokens=None):
    """Close a run: set status, finished_at, and computed duration_ms.

    `status` is 'success' or 'failed'. `finished_at` is the current UTC
    ISO-8601 string; `duration_ms` is the non-negative integer milliseconds
    from the row's stored `started_at` to now. `tokens_in`, `tokens_out`,
    `cost` (stored in `cost_usd`), `error`, `cache_read_tokens`, and
    `cache_creation_tokens` (the API usage fields `cache_read_input_tokens` /
    `cache_creation_input_tokens`) are written when provided and left as SQL
    NULL when None. Returns None; on any journal failure (including an unknown
    or None `run_id`) emits one warning and returns None without raising.
    """
    try:
        if run_id is None:
            raise ValueError("run_id is None")
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT started_at FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"unknown run_id: {run_id!r}")
            started_at = _parse_iso_utc(row[0])
            now = _utc_now()
            duration_ms = max(0, int((now - started_at).total_seconds() * 1000))
            conn.execute(
                """
                UPDATE runs
                SET status = ?, finished_at = ?, duration_ms = ?,
                    tokens_in = ?, tokens_out = ?, cost_usd = ?, error = ?,
                    cache_read_tokens = ?, cache_creation_tokens = ?
                WHERE id = ?
                """,
                (
                    status, now.isoformat(), duration_ms,
                    tokens_in, tokens_out, cost, error,
                    cache_read_tokens, cache_creation_tokens, run_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return None
    except Exception as exc:  # any journal failure is swallowed, never raised
        warnings.warn(f"run_journal: finish_run failed: {exc}")
        return None


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
    run_id = start_run(agent, task, metadata)
    try:
        yield run_id
    except Exception as exc:
        finish_run(run_id, "failed", error=str(exc))
        raise
    else:
        finish_run(run_id, "success")


# ---------------------------------------------------------------------------
# CLI: `stats` and `snapshot`
# ---------------------------------------------------------------------------


def _nearest_rank_index(count, percent):
    """1-indexed nearest-rank position for `percent` over `count` items."""
    rank = -(-(percent * count) // 100)  # ceil(percent * count / 100)
    return max(1, min(count, rank))


def _fetch_runs(project, db_path=None, agent=None):
    conn = _connect_readonly(db_path) if db_path else _connect()
    try:
        conn.row_factory = sqlite3.Row
        clauses, params = [], []
        if project:
            clauses.append("project = ?")
            params.append(project)
        if agent:
            clauses.append("agent = ?")
            params.append(agent)
        sql = "SELECT * FROM runs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _format_summary_line(label, rows):
    if len(label) > 20:
        label = label[:17] + "..."
    run_count = len(rows)
    finished = [row for row in rows if row["status"] in _FINISHED_STATUSES]
    total_tokens = sum(
        (row["tokens_in"] or 0) + (row["tokens_out"] or 0) for row in rows
    )
    total_cache_read = sum(
        _row_column(row, "cache_read_tokens") or 0 for row in rows
    )
    total_cache_creation = sum(
        _row_column(row, "cache_creation_tokens") or 0 for row in rows
    )
    total_cost = sum((row["cost_usd"] or 0) for row in rows)

    if finished:
        successes = sum(1 for row in finished if row["status"] == "success")
        rate_str = f"{successes / len(finished) * 100:.0f}%"
        durations = sorted(row["duration_ms"] for row in finished)
        p50 = durations[_nearest_rank_index(len(durations), 50) - 1]
        p95 = durations[_nearest_rank_index(len(durations), 95) - 1]
        p50_str, p95_str = str(p50), str(p95)
    else:
        rate_str = p50_str = p95_str = "—"

    return (
        f"{label:<20}{run_count:>6}{rate_str:>10}{p50_str:>8}{p95_str:>8}"
        f"{total_tokens:>10}{total_cache_read:>11}{total_cache_creation:>13}"
        f"{total_cost:>10.2f}"
    )


def _print_summary_table(title, key_label, ordered_groups):
    print(title)
    print(
        f"{key_label:<20}{'runs':>6}{'success%':>10}{'p50':>8}{'p95':>8}"
        f"{'tokens':>10}{'cache-read':>11}{'cache-create':>13}{'cost':>10}"
    )
    for label, rows in ordered_groups:
        print(_format_summary_line(label, rows))
    if not ordered_groups:
        print("(no runs)")


def _print_per_agent_table(rows):
    agents = {}
    for row in rows:
        agents.setdefault(row["agent"], []).append(row)
    ordered = [(agent, agents[agent]) for agent in sorted(agents)]
    _print_summary_table("Per-agent stats:", "agent", ordered)


def _row_column(row, name):
    # Snapshots taken before a column existed lack it entirely.
    return row[name] if name in row.keys() else None


def _print_per_version_table(rows):
    groups = {}
    for row in rows:
        version = _row_column(row, "template_version") or "—"
        groups.setdefault(version, []).append(row)
    # Chronological by each version's earliest run — the improvement timeline.
    ordered = sorted(
        groups.items(),
        key=lambda item: min(row["started_at"] for row in item[1]),
    )
    _print_summary_table("Per-version stats:", "version", ordered)


def _print_recent_runs(rows, last_n):
    print(f"Last {last_n} runs:")
    ordered = sorted(rows, key=lambda row: row["started_at"], reverse=True)
    if not ordered:
        print("(no runs)")
        return
    for row in ordered[:last_n]:
        duration = row["duration_ms"] if row["duration_ms"] is not None else "—"
        print(
            f"{row['started_at']}  {row['agent']:<15}{row['task']:<20}"
            f"{row['status']:<10}{duration}"
        )


def _print_failures(rows):
    print("Failures:")
    failed_rows = [row for row in rows if row["status"] == "failed"]
    if not failed_rows:
        print("(none)")
        return
    for row in failed_rows:
        print(
            f"{row['started_at']}  {row['agent']:<15}{row['task']:<20}"
            f"{row['error']}"
        )


def _run_stats(last_n, project, db_path=None, agent=None, by_version=False):
    rows = _fetch_runs(project, db_path, agent)
    if by_version:
        _print_per_version_table(rows)
        return
    _print_per_agent_table(rows)
    print()
    _print_recent_runs(rows, last_n)
    print()
    _print_failures(rows)


def _run_snapshot(dest):
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = _connect()
    try:
        # VACUUM INTO reads through the connection, so the copy includes
        # un-checkpointed WAL content and refuses an existing destination.
        conn.execute("VACUUM INTO ?", (dest,))
    finally:
        conn.close()
    print(f"snapshot written: {dest}")


def _build_arg_parser():
    parser = argparse.ArgumentParser(prog="run_journal")
    subparsers = parser.add_subparsers(dest="command")
    stats_parser = subparsers.add_parser("stats", help="Show run statistics")
    stats_parser.add_argument("--last", type=int, default=_DEFAULT_LAST_N)
    stats_parser.add_argument("--project", default=None)
    stats_parser.add_argument("--agent", default=None)
    stats_parser.add_argument(
        "--by-version", action="store_true",
        help="Summarize by template version, oldest first, instead of the default sections",
    )
    stats_parser.add_argument(
        "--db", default=None,
        help="Read this database file (e.g. a snapshot) instead of RUN_JOURNAL_DB",
    )
    snapshot_parser = subparsers.add_parser(
        "snapshot", help="Write a consistent single-file copy of the journal"
    )
    snapshot_parser.add_argument("dest")
    return parser


def main(argv=None):
    """CLI entry for `python -m run_journal`. Returns a process exit code (int).

    Parses `argv` (default `sys.argv[1:]`). The `stats` subcommand prints
    plain-text tables to stdout: a per-agent table (run count, success rate,
    p50/p95 duration_ms, total tokens, total cache reads/creations, total
    cost), the last N runs
    (`--last N`, default 10; status and duration), and failed runs with their
    error messages. `--project NAME` and `--agent NAME` filter all sections;
    `--by-version` prints one table of the same metrics grouped by recorded
    template version (oldest version first) instead; `--db PATH` reads that
    database file (e.g. a snapshot) read-only instead of
    `RUN_JOURNAL_DB`. The `snapshot DEST` subcommand writes a consistent
    single-file copy of the journal to `DEST` via `VACUUM INTO` (safe while
    other processes write; refuses an existing `DEST`). Returns 0 on success;
    on a journal failure emits one warning and returns a non-zero code without
    raising. Unrecognized or missing subcommands print usage and return a
    non-zero code.
    """
    if argv is None:
        argv = sys.argv[1:]
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if exc.code else 2

    if args.command == "stats":
        try:
            _run_stats(args.last, args.project, args.db, args.agent,
                       args.by_version)
            return 0
        except Exception as exc:  # any journal failure is swallowed, never raised
            warnings.warn(f"run_journal: stats failed: {exc}")
            return 1

    if args.command == "snapshot":
        try:
            _run_snapshot(args.dest)
            return 0
        except Exception as exc:  # any journal failure is swallowed, never raised
            warnings.warn(f"run_journal: snapshot failed: {exc}")
            return 1

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
