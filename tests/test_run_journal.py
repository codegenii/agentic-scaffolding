"""Table-driven tests for the run_journal module.

Every test isolates RUN_JOURNAL_DB to a fresh temp path (never the real
default `~/.agent-journal/runs.db`), per the machine-state invariant. Tests
that check the CLI or aggregate read paths seed rows directly through SQL so
they exercise `main`'s own logic independently of `start_run`/`finish_run`.
"""

import contextlib
import io
import json
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import unittest
import warnings
from datetime import datetime, timedelta, timezone

import run_journal


# ---------------------------------------------------------------------------
# Schema fixtures (mirrors the schema documented in the interface contract;
# used to seed rows directly so CLI tests do not depend on start_run/
# finish_run being correct).
# ---------------------------------------------------------------------------

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
    metadata    TEXT
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


class _Boom(Exception):
    """Exception used only to verify that record() re-raises unchanged."""


# ---------------------------------------------------------------------------
# File-private helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _chdir(path):
    """Temporarily change the working directory, restoring it afterward."""
    original = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


@contextlib.contextmanager
def _empty_path_environment():
    """Temporarily clear PATH so no `git` executable can be resolved."""
    original = os.environ.get("PATH")
    os.environ["PATH"] = ""
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = original


def _make_unwritable_db_path(root):
    """Return a db path whose parent segment is a regular file, not a dir."""
    blocker = os.path.join(root, "blocker")
    with open(blocker, "w", encoding="utf-8") as fh:
        fh.write("not a directory")
    return os.path.join(blocker, "runs.db")


def _seed_runs(db_path, rows):
    """Create the schema (if absent) and insert rows directly via SQL.

    Bypasses start_run/finish_run so CLI/read-path tests exercise main's own
    aggregation logic independently. Returns the inserted rowids in order.
    """
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_RUNS_TABLE_SQL)
        conn.execute(_EVENTS_TABLE_SQL)
        ids = []
        for row in rows:
            cur = conn.execute(
                """
                INSERT INTO runs
                    (project, agent, task, status, started_at, finished_at,
                     duration_ms, tokens_in, tokens_out, cost_usd, error,
                     metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["project"],
                    row["agent"],
                    row["task"],
                    row["status"],
                    row["started_at"],
                    row.get("finished_at"),
                    row.get("duration_ms"),
                    row.get("tokens_in"),
                    row.get("tokens_out"),
                    row.get("cost_usd"),
                    row.get("error"),
                    row.get("metadata"),
                ),
            )
            ids.append(cur.lastrowid)
        conn.commit()
        return ids
    finally:
        conn.close()


def _seed_running_run(db_path, started_at=None, **overrides):
    """Seed a single 'running' row and return its id."""
    if started_at is None:
        started_at = datetime.now(timezone.utc).isoformat()
    row = {
        "project": "proj",
        "agent": "agent",
        "task": "task",
        "status": "running",
        "started_at": started_at,
    }
    row.update(overrides)
    return _seed_runs(db_path, [row])[0]


def _finished_run(agent, duration_ms, status, *, project="proj", task="task",
                   tokens_in=None, tokens_out=None, cost_usd=None, error=None,
                   started_at=None):
    """Build a seed-able finished-run row dict."""
    if started_at is None:
        started_at = datetime.now(timezone.utc).isoformat()
    return {
        "project": project,
        "agent": agent,
        "task": task,
        "status": status,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "error": error,
        "metadata": None,
    }


def _running_run(agent, *, project="proj", task="task", tokens_in=None,
                  tokens_out=None, cost_usd=None, started_at=None):
    """Build a seed-able still-running row dict."""
    if started_at is None:
        started_at = datetime.now(timezone.utc).isoformat()
    return {
        "project": project,
        "agent": agent,
        "task": task,
        "status": "running",
        "started_at": started_at,
        "finished_at": None,
        "duration_ms": None,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "error": None,
        "metadata": None,
    }


def _seed_recency_dataset(db_path, count=12):
    """Seed `count` finished runs with distinct, sortable started_at values."""
    rows = [
        _finished_run(
            "agent",
            i,
            "success",
            task=f"task-{i:02d}",
            started_at=f"2026-01-01T00:00:{i:02d}+00:00",
        )
        for i in range(count)
    ]
    return _seed_runs(db_path, rows)


def _fetch_run(db_path, run_id):
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        return cur.fetchone()
    finally:
        conn.close()


def _fetch_events(db_path, run_id):
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM events WHERE run_id = ? ORDER BY id", (run_id,)
        )
        return cur.fetchall()
    finally:
        conn.close()


def _table_names(db_path):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def _journal_mode(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()


def _parse_iso8601_utc(value):
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _assert_recent_utc_timestamp(testcase, value, within_seconds=120):
    """Assert `value` is an ISO-8601 UTC string close to the current time."""
    testcase.assertIsInstance(value, str)
    parsed = _parse_iso8601_utc(value)
    delta = abs((datetime.now(timezone.utc) - parsed).total_seconds())
    testcase.assertLess(
        delta, within_seconds,
        f"timestamp {value!r} is not within {within_seconds}s of now",
    )


def _assert_standalone_integer(testcase, text, value):
    """Assert the integer `value` appears as a standalone number in `text`."""
    pattern = r"(?<!\d)" + re.escape(str(value)) + r"(?!\d)"
    testcase.assertRegex(text, pattern)


def _assert_standalone_amount(testcase, text, value):
    """Assert a decimal `value` appears, tolerant of trailing zero padding."""
    text_value = str(float(value))
    integer_part, frac_part = text_value.split(".")
    frac_part = frac_part.rstrip("0") or "0"
    pattern = (
        r"(?<!\d)" + re.escape(integer_part) + r"\." + re.escape(frac_part)
        + r"0*(?!\d)"
    )
    testcase.assertRegex(text, pattern)


def _assert_standalone_percentage(testcase, text, percent):
    """Assert a success-rate value appears as a percentage or a ratio."""
    as_percent = r"(?<!\d)" + re.escape(str(percent)) + r"(\.0+)?\s*%"
    as_ratio = r"(?<!\d)0\." + re.escape(str(percent)) + r"0*(?!\d)"
    testcase.assertRegex(text, as_percent + "|" + as_ratio)


def _capture_stdout(argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        exit_code = run_journal.main(list(argv))
    return exit_code, buffer.getvalue()


def _capture_stdout_and_stderr(argv):
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        exit_code = run_journal.main(list(argv))
    return exit_code, out.getvalue() + err.getvalue()


# ---------------------------------------------------------------------------
# Base test case
# ---------------------------------------------------------------------------


class _IsolatedJournalTestCase(unittest.TestCase):
    """Points RUN_JOURNAL_DB at a fresh temp path for the duration of a test."""

    def setUp(self):
        self._tempdir = tempfile.mkdtemp(prefix="run-journal-test-")
        self.db_path = os.path.join(self._tempdir, "nested", "runs.db")
        self._saved_env = {
            key: os.environ.get(key)
            for key in ("RUN_JOURNAL_DB", "RUN_JOURNAL_PROJECT")
        }
        os.environ["RUN_JOURNAL_DB"] = self.db_path
        os.environ.pop("RUN_JOURNAL_PROJECT", None)

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self._tempdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Path resolution and schema bootstrap
# ---------------------------------------------------------------------------


class PathAndSchemaBootstrapTests(_IsolatedJournalTestCase):
    """Covers RUN_JOURNAL_DB resolution, directory creation, schema, WAL."""

    def test_start_run_creates_missing_parent_directory_and_database_file(self):
        self.assertFalse(os.path.exists(self.db_path))

        run_journal.start_run("agent", "task")

        self.assertTrue(os.path.isdir(os.path.dirname(self.db_path)))
        self.assertTrue(os.path.isfile(self.db_path))

    def test_first_public_call_creates_runs_and_events_tables(self):
        run_journal.start_run("agent", "task")

        self.assertLessEqual({"runs", "events"}, _table_names(self.db_path))

    def test_database_is_in_wal_mode_after_a_public_call(self):
        run_journal.start_run("agent", "task")

        self.assertEqual(_journal_mode(self.db_path), "wal")


# ---------------------------------------------------------------------------
# Project name derivation
# ---------------------------------------------------------------------------


class ProjectDerivationTests(_IsolatedJournalTestCase):
    """Covers RUN_JOURNAL_PROJECT and the .git-ancestor walk in start_run."""

    def test_start_run_uses_run_journal_project_environment_variable_when_set(self):
        os.environ["RUN_JOURNAL_PROJECT"] = "explicit-project"

        run_id = run_journal.start_run("agent", "task")

        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["project"], "explicit-project")

    def test_start_run_derives_project_from_basename_of_git_directory_ancestor(self):
        with tempfile.TemporaryDirectory() as fixture_root:
            repo_dir = os.path.join(fixture_root, "my-repo")
            os.makedirs(os.path.join(repo_dir, ".git"))
            work_dir = os.path.join(repo_dir, "sub", "dir")
            os.makedirs(work_dir)
            with _chdir(work_dir):
                run_id = run_journal.start_run("agent", "task")

        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["project"], "my-repo")

    def test_start_run_derives_project_from_main_checkout_named_in_git_worktree_file(self):
        with tempfile.TemporaryDirectory() as fixture_root:
            main_checkout = os.path.join(fixture_root, "main-checkout")
            os.makedirs(os.path.join(main_checkout, ".git"))
            gitdir_target = os.path.join(
                main_checkout, ".git", "worktrees", "feature-branch"
            )
            os.makedirs(gitdir_target)
            worktree_dir = os.path.join(fixture_root, "somewhere-else")
            os.makedirs(worktree_dir)
            with open(
                os.path.join(worktree_dir, ".git"), "w", encoding="utf-8"
            ) as fh:
                fh.write("gitdir: " + gitdir_target.replace(os.sep, "/") + "\n")
            with _chdir(worktree_dir):
                run_id = run_journal.start_run("agent", "task")

        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["project"], "main-checkout")

    def test_start_run_derives_project_from_working_directory_when_no_git_ancestor_exists(self):
        with tempfile.TemporaryDirectory() as fixture_root:
            work_dir = os.path.join(fixture_root, "no-git-here")
            os.makedirs(work_dir)
            with _chdir(work_dir):
                run_id = run_journal.start_run("agent", "task")

        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["project"], "no-git-here")

    def test_start_run_derives_project_without_shelling_out_to_git(self):
        with tempfile.TemporaryDirectory() as fixture_root:
            repo_dir = os.path.join(fixture_root, "path-scrubbed-repo")
            os.makedirs(os.path.join(repo_dir, ".git"))
            with _chdir(repo_dir), _empty_path_environment():
                run_id = run_journal.start_run("agent", "task")

        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["project"], "path-scrubbed-repo")


# ---------------------------------------------------------------------------
# start_run
# ---------------------------------------------------------------------------


class StartRunTests(_IsolatedJournalTestCase):
    def test_start_run_inserts_a_running_row_with_the_given_agent_task_and_metadata(self):
        run_id = run_journal.start_run("agent-x", "do the thing", metadata={"k": "v"})

        self.assertIsInstance(run_id, int)
        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["agent"], "agent-x")
        self.assertEqual(row["task"], "do the thing")
        self.assertEqual(row["status"], "running")
        _assert_recent_utc_timestamp(self, row["started_at"])
        self.assertEqual(json.loads(row["metadata"]), {"k": "v"})
        self.assertIsNone(row["finished_at"])
        self.assertIsNone(row["duration_ms"])

    def test_start_run_returns_a_distinct_integer_id_for_each_call(self):
        first_id = run_journal.start_run("agent-x", "task-a")
        second_id = run_journal.start_run("agent-x", "task-b")

        self.assertIsInstance(first_id, int)
        self.assertIsInstance(second_id, int)
        self.assertNotEqual(first_id, second_id)

    def test_start_run_with_metadata_omitted_stores_null_metadata(self):
        run_id = run_journal.start_run("agent-x", "task-a")

        row = _fetch_run(self.db_path, run_id)
        self.assertIsNone(row["metadata"])


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------


class LogEventTests(_IsolatedJournalTestCase):
    def test_log_event_appends_a_row_with_the_given_type_and_payload(self):
        run_id = _seed_running_run(self.db_path)

        result = run_journal.log_event(run_id, "tool_call", payload={"foo": "bar"})

        self.assertIsNone(result)
        rows = _fetch_events(self.db_path, run_id)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["run_id"], run_id)
        self.assertEqual(row["type"], "tool_call")
        _assert_recent_utc_timestamp(self, row["ts"])
        self.assertEqual(json.loads(row["payload"]), {"foo": "bar"})

    def test_log_event_with_payload_omitted_stores_null_payload(self):
        run_id = _seed_running_run(self.db_path)

        run_journal.log_event(run_id, "heartbeat")

        rows = _fetch_events(self.db_path, run_id)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["payload"])

    def test_log_event_appends_independent_rows_for_multiple_calls(self):
        run_id = _seed_running_run(self.db_path)

        run_journal.log_event(run_id, "first")
        run_journal.log_event(run_id, "second", payload={"n": 2})

        rows = _fetch_events(self.db_path, run_id)
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["type"] for row in rows], ["first", "second"])


# ---------------------------------------------------------------------------
# finish_run
# ---------------------------------------------------------------------------


class FinishRunTests(_IsolatedJournalTestCase):
    def test_finish_run_sets_status_finished_at_and_a_realistic_nonnegative_duration(self):
        started_at = (
            datetime.now(timezone.utc) - timedelta(milliseconds=300)
        ).isoformat()
        run_id = _seed_running_run(self.db_path, started_at=started_at)

        result = run_journal.finish_run(run_id, "success")

        self.assertIsNone(result)
        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["status"], "success")
        _assert_recent_utc_timestamp(self, row["finished_at"])
        self.assertIsInstance(row["duration_ms"], int)
        self.assertGreaterEqual(row["duration_ms"], 250)
        self.assertLess(row["duration_ms"], 10000)

    def test_finish_run_writes_all_provided_optional_fields(self):
        run_id = _seed_running_run(self.db_path)

        result = run_journal.finish_run(
            run_id, "success", tokens_in=12, tokens_out=34, cost=0.5, error=None
        )

        self.assertIsNone(result)
        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["tokens_in"], 12)
        self.assertEqual(row["tokens_out"], 34)
        self.assertEqual(row["cost_usd"], 0.5)

    def test_finish_run_leaves_omitted_optional_fields_as_null(self):
        run_id = _seed_running_run(self.db_path)

        run_journal.finish_run(run_id, "failed")

        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["status"], "failed")
        self.assertIsNone(row["tokens_in"])
        self.assertIsNone(row["tokens_out"])
        self.assertIsNone(row["cost_usd"])
        self.assertIsNone(row["error"])

    def test_finish_run_records_the_given_error_message_on_failure(self):
        run_id = _seed_running_run(self.db_path)

        run_journal.finish_run(run_id, "failed", error="boom")

        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["error"], "boom")

    def test_finish_run_with_unknown_run_id_returns_none_and_warns_once(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = run_journal.finish_run(999999999, "success")

        self.assertIsNone(result)
        self.assertEqual(len(caught), 1)

    def test_finish_run_with_none_run_id_returns_none_and_warns_once(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = run_journal.finish_run(None, "success")

        self.assertIsNone(result)
        self.assertEqual(len(caught), 1)


# ---------------------------------------------------------------------------
# record() as a context manager
# ---------------------------------------------------------------------------


class RecordContextManagerTests(_IsolatedJournalTestCase):
    def test_record_as_context_manager_yields_run_id_and_marks_success_on_normal_exit(self):
        with run_journal.record("agent", "task") as run_id:
            pass

        self.assertIsInstance(run_id, int)
        row = _fetch_run(self.db_path, run_id)
        self.assertEqual(row["status"], "success")
        self.assertIsNotNone(row["finished_at"])
        self.assertIsInstance(row["duration_ms"], int)
        self.assertGreaterEqual(row["duration_ms"], 0)

    def test_record_context_manager_reraises_original_exception_and_marks_run_failed(self):
        captured_run_id = []

        with self.assertRaises(_Boom):
            with run_journal.record("agent", "task") as run_id:
                captured_run_id.append(run_id)
                raise _Boom("kaboom")

        row = _fetch_run(self.db_path, captured_run_id[0])
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["error"], "kaboom")

    def test_record_reraises_original_exception_even_when_its_own_journal_calls_fail(self):
        os.environ["RUN_JOURNAL_DB"] = _make_unwritable_db_path(self._tempdir)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with self.assertRaises(_Boom):
                with run_journal.record("agent", "task"):
                    raise _Boom("kaboom")

        self.assertGreaterEqual(len(caught), 1)


# ---------------------------------------------------------------------------
# record() as a decorator
# ---------------------------------------------------------------------------


class RecordDecoratorTests(_IsolatedJournalTestCase):
    def _latest_run_row(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1")
            return cur.fetchone()
        finally:
            conn.close()

    def test_record_as_decorator_returns_the_wrapped_functions_value_and_marks_success(self):
        @run_journal.record("agent", "task")
        def add(a, b):
            return a + b

        result = add(2, 3)

        self.assertEqual(result, 5)
        row = self._latest_run_row()
        self.assertEqual(row["status"], "success")

    def test_record_as_decorator_passes_through_positional_and_keyword_arguments(self):
        @run_journal.record("agent", "task")
        def greet(name, *, greeting="hello"):
            return f"{greeting}, {name}!"

        result = greet("world", greeting="hi")

        self.assertEqual(result, "hi, world!")

    def test_record_as_decorator_creates_an_independent_run_for_each_invocation(self):
        @run_journal.record("agent", "task")
        def noop():
            return None

        noop()
        noop()

        conn = sqlite3.connect(self.db_path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM runs WHERE agent = ? AND task = ?"
                " AND status = ?",
                ("agent", "task", "success"),
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 2)

    def test_record_as_decorator_reraises_and_marks_failed_when_wrapped_function_raises(self):
        @run_journal.record("agent", "task")
        def boom():
            raise _Boom("kaboom")

        with self.assertRaises(_Boom):
            boom()

        row = self._latest_run_row()
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["error"], "kaboom")


# ---------------------------------------------------------------------------
# Journal-failure policy (returns None, warns once, never raises)
# ---------------------------------------------------------------------------


class JournalFailurePolicyTests(_IsolatedJournalTestCase):
    def test_start_run_with_unwritable_database_path_returns_none_and_warns_once(self):
        os.environ["RUN_JOURNAL_DB"] = _make_unwritable_db_path(self._tempdir)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = run_journal.start_run("agent", "task")

        self.assertIsNone(result)
        self.assertEqual(len(caught), 1)

    def test_start_run_with_non_json_serializable_metadata_returns_none_and_warns_once(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = run_journal.start_run("agent", "task", metadata={"bad": object()})

        self.assertIsNone(result)
        self.assertEqual(len(caught), 1)

    def test_log_event_with_non_json_serializable_payload_returns_none_and_warns_once(self):
        run_id = _seed_running_run(self.db_path)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = run_journal.log_event(run_id, "type", payload={"bad": object()})

        self.assertIsNone(result)
        self.assertEqual(len(caught), 1)

    def test_finish_run_with_unwritable_database_path_returns_none_and_warns_once(self):
        run_id = _seed_running_run(self.db_path)
        os.environ["RUN_JOURNAL_DB"] = _make_unwritable_db_path(self._tempdir)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = run_journal.finish_run(run_id, "success")

        self.assertIsNone(result)
        self.assertEqual(len(caught), 1)


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class ConcurrencyTests(_IsolatedJournalTestCase):
    def test_concurrent_start_run_calls_from_multiple_threads_all_commit(self):
        thread_count = 8
        results = [None] * thread_count
        errors = [None] * thread_count

        def worker(index):
            try:
                results[index] = run_journal.start_run(f"agent-{index}", "task")
            except Exception as exc:  # re-raised on the main thread below
                errors[index] = exc

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(thread_count)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        for thread in threads:
            self.assertFalse(thread.is_alive())
        for error in errors:
            if error is not None:
                raise error

        self.assertNotIn(None, results)
        self.assertEqual(len(set(results)), thread_count)

        conn = sqlite3.connect(self.db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, thread_count)

    def test_concurrent_finish_run_calls_from_multiple_threads_all_commit(self):
        thread_count = 8
        run_ids = _seed_runs(
            self.db_path,
            [_running_run("agent") for _ in range(thread_count)],
        )
        results = [None] * thread_count
        errors = [None] * thread_count

        def worker(index):
            status = "success" if index % 2 == 0 else "failed"
            try:
                results[index] = run_journal.finish_run(run_ids[index], status)
            except Exception as exc:  # re-raised on the main thread below
                errors[index] = exc

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(thread_count)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        for thread in threads:
            self.assertFalse(thread.is_alive())
        for error in errors:
            if error is not None:
                raise error

        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows_by_id = {
                row["id"]: row for row in conn.execute("SELECT * FROM runs").fetchall()
            }
        finally:
            conn.close()

        for index, run_id in enumerate(run_ids):
            row = rows_by_id[run_id]
            expected_status = "success" if index % 2 == 0 else "failed"
            self.assertEqual(row["status"], expected_status)
            self.assertIsNotNone(row["finished_at"])
            self.assertIsInstance(row["duration_ms"], int)
            self.assertGreaterEqual(row["duration_ms"], 0)


# ---------------------------------------------------------------------------
# CLI: `stats` per-agent table
# ---------------------------------------------------------------------------


class CliStatsPerAgentTableTests(_IsolatedJournalTestCase):
    def test_stats_prints_per_agent_run_count_success_rate_percentiles_tokens_and_cost(self):
        _seed_runs(
            self.db_path,
            [
                _finished_run(
                    "alpha", 100, "success", tokens_in=10, tokens_out=5, cost_usd=0.25
                ),
                _finished_run(
                    "alpha", 200, "success", tokens_in=20, tokens_out=None, cost_usd=None
                ),
                _finished_run(
                    "alpha", 300, "failed", tokens_in=None, tokens_out=15,
                    cost_usd=0.5, error="boom1",
                ),
                _finished_run(
                    "alpha", 400, "success", tokens_in=5, tokens_out=5, cost_usd=0.25
                ),
            ],
        )

        exit_code, output = _capture_stdout(["stats"])

        self.assertEqual(exit_code, 0)
        self.assertIn("alpha", output)
        _assert_standalone_integer(self, output, 4)  # run count
        _assert_standalone_percentage(self, output, 75)  # success rate 3/4
        _assert_standalone_integer(self, output, 200)  # p50 duration_ms
        _assert_standalone_integer(self, output, 400)  # p95 duration_ms
        _assert_standalone_integer(self, output, 60)  # total tokens (35 + 25)
        _assert_standalone_amount(self, output, 1.0)  # total cost

    def test_stats_shows_em_dash_for_rate_and_percentiles_when_agent_has_no_finished_runs(self):
        _seed_runs(
            self.db_path,
            [
                _running_run("beta", tokens_in=15, tokens_out=5, cost_usd=0.25),
                _running_run("beta", tokens_in=None, tokens_out=None, cost_usd=None),
            ],
        )

        exit_code, output = _capture_stdout(["stats"])

        self.assertEqual(exit_code, 0)
        self.assertIn("beta", output)
        self.assertIn("—", output)
        _assert_standalone_integer(self, output, 2)  # run count
        _assert_standalone_integer(self, output, 20)  # total tokens (15 + 5)
        _assert_standalone_amount(self, output, 0.25)  # total cost

    def test_stats_percentiles_for_a_single_finished_run_equal_its_own_duration(self):
        _seed_runs(self.db_path, [_finished_run("solo", 250, "success")])

        exit_code, output = _capture_stdout(["stats"])

        self.assertEqual(exit_code, 0)
        self.assertIn("solo", output)
        _assert_standalone_integer(self, output, 250)


# ---------------------------------------------------------------------------
# CLI: `stats --last`
# ---------------------------------------------------------------------------


class CliStatsLastRunsTests(_IsolatedJournalTestCase):
    def test_stats_last_prints_the_n_most_recent_runs_in_descending_started_at_order(self):
        _seed_recency_dataset(self.db_path, count=12)

        exit_code, output = _capture_stdout(["stats", "--last", "3"])

        self.assertEqual(exit_code, 0)
        for name in ("task-11", "task-10", "task-09"):
            self.assertIn(name, output)
        for name in ("task-08", "task-00"):
            self.assertNotIn(name, output)
        self.assertLess(output.index("task-11"), output.index("task-10"))
        self.assertLess(output.index("task-10"), output.index("task-09"))

    def test_stats_last_defaults_to_ten_when_omitted(self):
        _seed_recency_dataset(self.db_path, count=12)

        exit_code, output = _capture_stdout(["stats"])

        self.assertEqual(exit_code, 0)
        for i in range(2, 12):
            self.assertIn(f"task-{i:02d}", output)
        self.assertNotIn("task-00", output)
        self.assertNotIn("task-01", output)


# ---------------------------------------------------------------------------
# CLI: `stats` failures section
# ---------------------------------------------------------------------------


class CliStatsFailuresSectionTests(_IsolatedJournalTestCase):
    def test_stats_lists_failed_runs_with_their_error_messages(self):
        _seed_runs(
            self.db_path,
            [
                _finished_run("agent", 10, "failed", error="boom-one"),
                _finished_run("agent", 20, "failed", error="boom-two"),
                _finished_run("agent", 30, "success"),
            ],
        )

        exit_code, output = _capture_stdout(["stats"])

        self.assertEqual(exit_code, 0)
        self.assertIn("boom-one", output)
        self.assertIn("boom-two", output)


# ---------------------------------------------------------------------------
# CLI: `stats --project`
# ---------------------------------------------------------------------------


class CliStatsProjectFilterTests(_IsolatedJournalTestCase):
    def test_stats_project_filter_restricts_all_sections_to_the_matching_project(self):
        _seed_runs(
            self.db_path,
            [
                _finished_run(
                    "agent-A", 10, "success", project="proj-A", task="task-A-last"
                ),
                _finished_run(
                    "agent-A", 20, "failed", project="proj-A", task="task-A-fail",
                    error="err-A-fail",
                ),
                _finished_run(
                    "agent-B", 10, "success", project="proj-B", task="task-B-last"
                ),
                _finished_run(
                    "agent-B", 20, "failed", project="proj-B", task="task-B-fail",
                    error="err-B-fail",
                ),
            ],
        )

        exit_code, output = _capture_stdout(["stats", "--project", "proj-A"])

        self.assertEqual(exit_code, 0)
        for token in ("agent-A", "task-A-last", "err-A-fail"):
            self.assertIn(token, output)
        for token in ("agent-B", "task-B-last", "err-B-fail"):
            self.assertNotIn(token, output)


# ---------------------------------------------------------------------------
# CLI: exit codes and edge cases
# ---------------------------------------------------------------------------


class CliStatsExitCodeAndEdgeCaseTests(_IsolatedJournalTestCase):
    def test_stats_returns_zero_on_success(self):
        _seed_runs(self.db_path, [_finished_run("agent", 10, "success")])

        exit_code, _output = _capture_stdout(["stats"])

        self.assertEqual(exit_code, 0)

    def test_stats_returns_nonzero_and_warns_once_on_journal_read_failure(self):
        os.environ["RUN_JOURNAL_DB"] = _make_unwritable_db_path(self._tempdir)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exit_code, _output = _capture_stdout(["stats"])

        self.assertNotEqual(exit_code, 0)
        self.assertEqual(len(caught), 1)

    def test_stats_on_empty_journal_returns_zero_and_prints_placeholder_sections(self):
        # self.db_path has never been touched by any public call before this.
        exit_code, output = _capture_stdout(["stats"])

        self.assertEqual(exit_code, 0)
        self.assertGreater(len(output), 0)

    def test_main_with_missing_subcommand_prints_usage_and_returns_nonzero(self):
        exit_code, output = _capture_stdout_and_stderr([])

        self.assertNotEqual(exit_code, 0)
        self.assertRegex(output, r"(?i)usage")

    def test_main_with_unrecognized_subcommand_prints_usage_and_returns_nonzero(self):
        exit_code, output = _capture_stdout_and_stderr(["bogus-subcommand"])

        self.assertNotEqual(exit_code, 0)
        self.assertRegex(output, r"(?i)usage")


if __name__ == "__main__":
    unittest.main()
