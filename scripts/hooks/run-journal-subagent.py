"""run-journal-subagent.py — journal every subagent run from this repo's sessions.

Registered in `.claude/settings.json` for two hook events and dispatched on
`hook_event_name`; writes one `runs` row per subagent run through
`run_journal` (machine-wide database, `RUN_JOURNAL_DB`):

- `SubagentStop` — fires at true completion in both spawn modes. A stopping
  agent listed in the payload's `background_tasks` was a background run:
  record it here (task from that entry's description, `started_at` and token
  totals from the agent transcript). Otherwise the run was synchronous and
  the richer `PostToolUse` event is milliseconds away: only stash the
  transcript path for it.
- `PostToolUse` (matcher `Agent|Task`) — for background spawns this fires at
  launch with status `async_launched`: ignored. For synchronous spawns it
  fires after `SubagentStop` with the run's description, `totalDurationMs`,
  and terminal status: record the row, token totals from the stashed
  transcript path.

Token totals are summed from the transcript's assistant lines, keeping only
the last line per API message id — streaming appends several lines per
message, and the harness's own `tool_response.usage` holds just the final
message, not the run. `cost_usd` stays NULL: the harness exposes no price.
A resumed agent (SendMessage) stops more than once; a marker file keeps the
first recording and skips the rest, so resumed work is undercounted.

State lives under `RUN_JOURNAL_HOOK_STATE_DIR` (default
`<tempdir>/run-journal-hook-state`), keyed by session and agent id; entries
older than 7 days are pruned opportunistically. Observe-only: every failure
exits 0 and never blocks the session.
"""

import datetime
import json
import os
import sys
import tempfile
import time

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_USAGE_KEYS = ("input_tokens", "output_tokens",
               "cache_read_input_tokens", "cache_creation_input_tokens")
_ASYNC_LAUNCH_STATUS = "async_launched"
_COMPLETED_STATUS = "completed"
_STATE_MAX_AGE_SECONDS = 7 * 24 * 3600
_STOP_STATE_WAIT_TRIES = 10
_STOP_STATE_WAIT_INTERVAL = 0.1
_TASK_SNIPPET_LIMIT = 80


def _state_dir():
    path = os.environ.get("RUN_JOURNAL_HOOK_STATE_DIR")
    if not path:
        path = os.path.join(tempfile.gettempdir(), "run-journal-hook-state")
    os.makedirs(path, exist_ok=True)
    return path


def _state_path(payload, agent_id, kind):
    session = payload.get("session_id") or "nosession"
    return os.path.join(_state_dir(), f"{session}-{agent_id}.{kind}")


def _prune_stale_state():
    cutoff = time.time() - _STATE_MAX_AGE_SECONDS
    try:
        with os.scandir(_state_dir()) as entries:
            for entry in entries:
                if entry.is_file() and entry.stat().st_mtime < cutoff:
                    os.unlink(entry.path)
    except OSError:
        pass


def _parse_transcript(path):
    """Return (first_timestamp, usage_totals) from a transcript JSONL file.

    `usage_totals` is a dict over `_USAGE_KEYS`, summed over distinct
    assistant message ids (last line per id wins), or None when the file
    yields no usage at all.
    """
    per_message = {}
    first_ts = None
    lines_seen = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            lines_seen += 1
            ts = obj.get("timestamp")
            if first_ts is None and isinstance(ts, str) and ts:
                first_ts = ts
            if obj.get("type") != "assistant":
                continue
            message = obj.get("message") or {}
            usage = message.get("usage")
            if not isinstance(usage, dict) or not usage:
                continue
            key = message.get("id") or f"line-{lines_seen}"
            per_message[key] = usage
    if not per_message:
        return first_ts, None
    totals = dict.fromkeys(_USAGE_KEYS, 0)
    for usage in per_message.values():
        for usage_key in _USAGE_KEYS:
            value = usage.get(usage_key)
            if isinstance(value, (int, float)):
                totals[usage_key] += int(value)
    return first_ts, totals


def _first_user_snippet(path):
    """First user message's text, whitespace-collapsed and truncated."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if obj.get("type") != "user":
                continue
            content = (obj.get("message") or {}).get("content")
            if isinstance(content, list):
                content = " ".join(
                    block.get("text", "") for block in content
                    if isinstance(block, dict) and block.get("type") == "text")
            if not isinstance(content, str):
                return None
            snippet = " ".join(content.split())
            return snippet[:_TASK_SNIPPET_LIMIT] or None
    return None


def _iso_or_none(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value.replace("Z", "+00:00")


def _record(run_journal, agent, task, status, metadata, started_at,
            usage, error=None):
    run_id = run_journal.start_run(agent, task, metadata=metadata,
                                   started_at=started_at)
    usage = usage or {}
    run_journal.finish_run(
        run_id, status,
        tokens_in=usage.get("input_tokens"),
        tokens_out=usage.get("output_tokens"),
        cache_read_tokens=usage.get("cache_read_input_tokens"),
        cache_creation_tokens=usage.get("cache_creation_input_tokens"),
        error=error,
    )


def _handle_subagent_stop(run_journal, payload):
    agent_id = payload.get("agent_id")
    if not agent_id:
        return
    if os.path.exists(_state_path(payload, agent_id, "recorded")):
        return
    transcript = payload.get("agent_transcript_path") or ""

    own_entry = next(
        (entry for entry in payload.get("background_tasks") or []
         if isinstance(entry, dict) and entry.get("id") == agent_id), None)
    if own_entry is None:
        # Synchronous run: PostToolUse follows with the full picture; it only
        # lacks the transcript location, so hand that over and write no row.
        with open(_state_path(payload, agent_id, "stop"), "w",
                  encoding="utf-8") as fh:
            json.dump({"transcript": transcript}, fh)
        return

    first_ts, usage = (None, None)
    task = None
    if transcript and os.path.exists(transcript):
        first_ts, usage = _parse_transcript(transcript)
        task = _first_user_snippet(transcript)
    if own_entry.get("description"):
        task = own_entry["description"]
    metadata = {"source": "subagent-hook", "background": True,
                "session_id": payload.get("session_id"),
                "agent_id": agent_id}
    _record(run_journal, payload.get("agent_type") or "subagent",
            task or "(subagent)", "success", metadata,
            _iso_or_none(first_ts), usage)
    with open(_state_path(payload, agent_id, "recorded"), "w",
              encoding="utf-8") as fh:
        fh.write("")


def _handle_post_tool_use(run_journal, payload):
    response = payload.get("tool_response")
    if not isinstance(response, dict):
        return
    status = response.get("status")
    if status == _ASYNC_LAUNCH_STATUS:
        return
    agent_id = response.get("agentId")
    if not agent_id:
        return
    if os.path.exists(_state_path(payload, agent_id, "recorded")):
        return

    # SubagentStop fires a beat earlier and stashes the transcript path;
    # give a slow hook runner a moment before settling for no tokens.
    stop_state_path = _state_path(payload, agent_id, "stop")
    for _ in range(_STOP_STATE_WAIT_TRIES):
        if os.path.exists(stop_state_path):
            break
        time.sleep(_STOP_STATE_WAIT_INTERVAL)
    usage = None
    started_at = None
    try:
        with open(stop_state_path, encoding="utf-8") as fh:
            transcript = json.load(fh).get("transcript") or ""
        if transcript and os.path.exists(transcript):
            first_ts, usage = _parse_transcript(transcript)
            started_at = _iso_or_none(first_ts)
    except (OSError, ValueError):
        pass

    duration_ms = response.get("totalDurationMs") or payload.get("duration_ms")
    if started_at is None and isinstance(duration_ms, (int, float)):
        started = (datetime.datetime.now(datetime.timezone.utc)
                   - datetime.timedelta(milliseconds=duration_ms))
        started_at = started.isoformat()

    tool_input = payload.get("tool_input") or {}
    agent = (tool_input.get("subagent_type")
             or response.get("agentType") or "subagent")
    task = (tool_input.get("description")
            or " ".join(str(tool_input.get("prompt") or "").split())
            [:_TASK_SNIPPET_LIMIT]
            or "(subagent)")
    metadata = {"source": "subagent-hook", "background": False,
                "session_id": payload.get("session_id"),
                "agent_id": agent_id,
                "model": response.get("resolvedModel"),
                "tool_use_count": response.get("totalToolUseCount")}
    if status == _COMPLETED_STATUS:
        _record(run_journal, agent, task, "success", metadata, started_at,
                usage)
    else:
        _record(run_journal, agent, task, "failed", metadata, started_at,
                usage, error=f"subagent status: {status}")
    with open(_state_path(payload, agent_id, "recorded"), "w",
              encoding="utf-8") as fh:
        fh.write("")


def main():
    try:
        payload = json.load(sys.stdin)
        sys.path.insert(0, _REPO_ROOT)
        import run_journal
        _prune_stale_state()
        event = payload.get("hook_event_name")
        if event == "SubagentStop":
            _handle_subagent_stop(run_journal, payload)
        elif event == "PostToolUse":
            _handle_post_tool_use(run_journal, payload)
    except Exception:  # observe-only: a journal hook must never block work
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
