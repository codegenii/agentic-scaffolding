"""Tests for scripts/hooks/run-journal-subagent.py, run by execution.

Each test launches the hook script as a real subprocess — the way the
harness runs it — with a synthetic hook payload on stdin, RUN_JOURNAL_DB and
RUN_JOURNAL_HOOK_STATE_DIR pointed at fresh temp paths, and an explicit
RUN_JOURNAL_PROJECT so no test depends on the checkout it runs from.
Payload shapes mirror ones captured from Claude Code 2.1.215.
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

_WORKTREE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HOOK_PATH = os.path.join(_WORKTREE_ROOT, "scripts", "hooks",
                          "run-journal-subagent.py")

_AGENT_ID = "agent123abc"
_SESSION_ID = "sess-1111"

# One streamed run: message msg_a appears twice (streaming rewrites the same
# message id with growing output), msg_b once. Correct aggregation keeps the
# last line per id: tokens_in 18, tokens_out 255, cache_read 14968,
# cache_creation 15661.
_EXPECTED_TOKENS_IN = 18
_EXPECTED_TOKENS_OUT = 255
_EXPECTED_CACHE_READ = 14968
_EXPECTED_CACHE_CREATION = 15661


def _write_transcript(path, first_ts, user_text="Investigate the widget"):
    def usage(i, o, cr, cc):
        return {"input_tokens": i, "output_tokens": o,
                "cache_read_input_tokens": cr,
                "cache_creation_input_tokens": cc}

    lines = [
        {"type": "mode", "mode": "normal"},
        {"type": "user", "timestamp": first_ts,
         "message": {"role": "user", "content": user_text}},
        {"type": "assistant", "timestamp": first_ts,
         "message": {"id": "msg_a", "usage": usage(10, 3, 0, 14968)}},
        {"type": "assistant", "timestamp": first_ts,
         "message": {"id": "msg_a", "usage": usage(10, 206, 0, 14968)}},
        {"type": "user", "timestamp": first_ts,
         "message": {"role": "user",
                     "content": [{"type": "tool_result", "content": "ok"}]}},
        {"type": "assistant", "timestamp": first_ts,
         "message": {"id": "msg_b", "usage": usage(8, 49, 14968, 693)}},
    ]
    with open(path, "w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")


def _stop_payload(transcript_path, background=True, description=None):
    background_tasks = []
    if background:
        entry = {"id": _AGENT_ID, "type": "subagent", "status": "running",
                 "agent_type": "implementer"}
        if description is not None:
            entry["description"] = description
        background_tasks.append(entry)
    return {
        "session_id": _SESSION_ID,
        "hook_event_name": "SubagentStop",
        "permission_mode": "default",
        "agent_id": _AGENT_ID,
        "agent_type": "implementer",
        "agent_transcript_path": transcript_path,
        "last_assistant_message": "done",
        "stop_hook_active": False,
        "background_tasks": background_tasks,
        "session_crons": [],
    }


def _post_payload(status="completed", duration_ms=12094):
    return {
        "session_id": _SESSION_ID,
        "hook_event_name": "PostToolUse",
        "permission_mode": "default",
        "tool_name": "Agent",
        "tool_input": {"description": "Phase 5 write tests",
                       "prompt": "Write the failing tests for the widget.",
                       "subagent_type": "test-writer",
                       "run_in_background": False},
        "tool_response": {"status": status, "agentId": _AGENT_ID,
                          "agentType": "test-writer",
                          "content": [{"type": "text", "text": "done"}],
                          "resolvedModel": "claude-haiku-4-5",
                          "totalDurationMs": duration_ms,
                          "totalTokens": 15718, "totalToolUseCount": 2},
        "tool_use_id": "toolu_x",
        "duration_ms": duration_ms,
    }


class _HookTestCase(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.mkdtemp(prefix="run-journal-hook-test-")
        self.db_path = os.path.join(self._tempdir, "runs.db")
        self.state_dir = os.path.join(self._tempdir, "state")
        self.transcript_path = os.path.join(self._tempdir, "agent.jsonl")
        self.first_ts = (datetime.now(timezone.utc)
                         - timedelta(seconds=90)).isoformat()
        _write_transcript(self.transcript_path, self.first_ts)

    def _run_hook(self, payload):
        env = dict(os.environ)
        env["RUN_JOURNAL_DB"] = self.db_path
        env["RUN_JOURNAL_HOOK_STATE_DIR"] = self.state_dir
        env["RUN_JOURNAL_PROJECT"] = "hooktest"
        env.pop("RUN_JOURNAL_TEMPLATE_VERSION", None)
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            [sys.executable, _HOOK_PATH], input=stdin, env=env,
            capture_output=True, text=True, timeout=60)

    def _fetch_runs(self):
        if not os.path.exists(self.db_path):
            return []
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM runs ORDER BY id").fetchall()
        finally:
            conn.close()

    def _state_file(self, kind):
        return os.path.join(self.state_dir,
                            f"{_SESSION_ID}-{_AGENT_ID}.{kind}")


class SubagentStopBackgroundTests(_HookTestCase):
    def test_records_one_finished_row_from_transcript_and_description(self):
        result = self._run_hook(_stop_payload(
            self.transcript_path, description="Phase 6 implement widget"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        rows = self._fetch_runs()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["agent"], "implementer")
        self.assertEqual(row["task"], "Phase 6 implement widget")
        self.assertEqual(row["status"], "success")
        self.assertEqual(row["project"], "hooktest")
        self.assertEqual(row["started_at"], self.first_ts)
        self.assertGreaterEqual(row["duration_ms"], 90_000)
        self.assertLess(row["duration_ms"], 90_000 + 60_000)
        self.assertEqual(row["tokens_in"], _EXPECTED_TOKENS_IN)
        self.assertEqual(row["tokens_out"], _EXPECTED_TOKENS_OUT)
        self.assertEqual(row["cache_read_tokens"], _EXPECTED_CACHE_READ)
        self.assertEqual(row["cache_creation_tokens"],
                         _EXPECTED_CACHE_CREATION)
        metadata = json.loads(row["metadata"])
        self.assertEqual(metadata["source"], "subagent-hook")
        self.assertTrue(metadata["background"])
        self.assertEqual(metadata["agent_id"], _AGENT_ID)
        self.assertTrue(os.path.exists(self._state_file("recorded")))

    def test_second_stop_for_the_same_agent_does_not_record_again(self):
        payload = _stop_payload(self.transcript_path, description="d")

        self._run_hook(payload)
        result = self._run_hook(payload)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(self._fetch_runs()), 1)

    def test_task_falls_back_to_first_user_message_without_a_description(self):
        result = self._run_hook(_stop_payload(self.transcript_path))

        self.assertEqual(result.returncode, 0)
        rows = self._fetch_runs()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["task"], "Investigate the widget")

    def test_missing_transcript_still_records_with_null_tokens(self):
        payload = _stop_payload(os.path.join(self._tempdir, "absent.jsonl"),
                                description="d")

        result = self._run_hook(payload)

        self.assertEqual(result.returncode, 0)
        rows = self._fetch_runs()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["tokens_in"])
        self.assertIsNone(rows[0]["tokens_out"])


class SubagentStopForegroundTests(_HookTestCase):
    def test_stashes_transcript_path_and_writes_no_row(self):
        result = self._run_hook(_stop_payload(self.transcript_path,
                                              background=False))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._fetch_runs(), [])
        with open(self._state_file("stop"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["transcript"],
                             self.transcript_path)


class PostToolUseTests(_HookTestCase):
    def test_async_launch_writes_no_row(self):
        result = self._run_hook(_post_payload(status="async_launched"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._fetch_runs(), [])

    def test_completed_run_uses_stashed_transcript_for_tokens_and_start(self):
        self._run_hook(_stop_payload(self.transcript_path, background=False))

        result = self._run_hook(_post_payload())

        self.assertEqual(result.returncode, 0)
        rows = self._fetch_runs()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["agent"], "test-writer")
        self.assertEqual(row["task"], "Phase 5 write tests")
        self.assertEqual(row["status"], "success")
        self.assertEqual(row["started_at"], self.first_ts)
        self.assertEqual(row["tokens_in"], _EXPECTED_TOKENS_IN)
        self.assertEqual(row["tokens_out"], _EXPECTED_TOKENS_OUT)
        self.assertEqual(row["cache_read_tokens"], _EXPECTED_CACHE_READ)
        self.assertEqual(row["cache_creation_tokens"],
                         _EXPECTED_CACHE_CREATION)
        metadata = json.loads(row["metadata"])
        self.assertFalse(metadata["background"])
        self.assertEqual(metadata["model"], "claude-haiku-4-5")
        self.assertEqual(metadata["tool_use_count"], 2)
        self.assertTrue(os.path.exists(self._state_file("recorded")))

    def test_completed_run_without_stash_backdates_start_by_total_duration(self):
        result = self._run_hook(_post_payload(duration_ms=12094))

        self.assertEqual(result.returncode, 0)
        rows = self._fetch_runs()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIsNone(row["tokens_in"])
        # Duration derives from the backdated start; allow for the hook's
        # one-second stash wait plus process overhead.
        self.assertGreaterEqual(row["duration_ms"], 12_000)
        self.assertLess(row["duration_ms"], 42_000)

    def test_terminal_non_completed_status_records_a_failed_row(self):
        result = self._run_hook(_post_payload(status="errored"))

        self.assertEqual(result.returncode, 0)
        rows = self._fetch_runs()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "failed")
        self.assertEqual(rows[0]["error"], "subagent status: errored")

    def test_stop_then_post_for_the_same_agent_records_once(self):
        self._run_hook(_stop_payload(self.transcript_path,
                                     description="d"))

        result = self._run_hook(_post_payload())

        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(self._fetch_runs()), 1)


class HookRobustnessTests(_HookTestCase):
    def test_malformed_stdin_exits_zero_and_writes_nothing(self):
        result = self._run_hook("this is not json")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._fetch_runs(), [])

    def test_unknown_event_name_exits_zero_and_writes_nothing(self):
        result = self._run_hook({"hook_event_name": "SessionStart"})

        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._fetch_runs(), [])

    def test_stale_state_files_are_pruned(self):
        os.makedirs(self.state_dir, exist_ok=True)
        stale = os.path.join(self.state_dir, "old-session-old-agent.stop")
        with open(stale, "w", encoding="utf-8") as fh:
            fh.write("{}")
        eight_days_ago = time.time() - 8 * 24 * 3600
        os.utime(stale, (eight_days_ago, eight_days_ago))

        result = self._run_hook(_stop_payload(self.transcript_path,
                                              background=False))

        self.assertEqual(result.returncode, 0)
        self.assertFalse(os.path.exists(stale))


if __name__ == "__main__":
    unittest.main()
