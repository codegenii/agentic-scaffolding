#!/usr/bin/env bash
# init-run-journal.sh — one-time machine bootstrap for the run-journal database.
#
# The journal bootstraps itself on first use (parent directory, database file,
# schema, WAL mode), but journal failures are swallowed by design — a broken
# path would record nothing, silently. This script runs the same bootstrap
# eagerly and fails loudly, and prints how to persist a custom location.
# Idempotent — safe to re-run.
#
# Usage:
#   ./scripts/init-run-journal.sh                     # default ~/.agent-journal/runs.db
#   ./scripts/init-run-journal.sh /custom/dir/runs.db # custom location

set -euo pipefail

log() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

cd "$(dirname "$0")/.."  # repo root — run_journal.py lives here

command -v python >/dev/null 2>&1 || die "python not found on PATH"

DEFAULT_DB=$(python -c "import os; print(os.path.join(os.path.expanduser('~'), '.agent-journal', 'runs.db').replace(os.sep, '/'))")
DB_PATH="${1:-$DEFAULT_DB}"

# WAL is unsafe on network filesystems — refuse UNC paths outright.
case "$DB_PATH" in
  //*|\\\\*) die "network path: WAL-mode SQLite is unsafe on network filesystems — pick a local path" ;;
esac

# Git Bash / MSYS: hand python a Windows-native path, not a /c/... one.
if command -v cygpath >/dev/null 2>&1; then
  converted=$(cygpath -m "$DB_PATH") || die "cannot resolve path: $DB_PATH"
  DB_PATH="$converted"
fi
DB_PATH=$(python -c "import os, sys; print(os.path.abspath(sys.argv[1]).replace(os.sep, '/'))" "$DB_PATH")

# The journal is machine-level state shared by every checkout and worktree — a
# path inside a repo fragments per worktree and dies with worktree cleanup
# (see .claude/agents/conventions/invariants.md).
REPO_ROOT=$(python -c "import os; print(os.path.abspath('.').replace(os.sep, '/'))")
case "$DB_PATH" in
  "$REPO_ROOT"/*) die "$DB_PATH is inside this checkout — the journal must live outside every repo" ;;
esac

# `stats` bootstraps through the module's own connection path (directory,
# database, schema, WAL) and exits non-zero on failure.
RUN_JOURNAL_DB="$DB_PATH" python -m run_journal stats >/dev/null \
  || die "bootstrap failed for $DB_PATH (see warning above)"

# Independent post-check: right file, right mode, right tables.
python - "$DB_PATH" <<'PY'
import sqlite3
import sys

conn = sqlite3.connect(sys.argv[1])
mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
conn.close()
if mode != "wal" or not {"runs", "events"} <= tables:
    sys.exit(f"unexpected database state: journal_mode={mode} tables={sorted(tables)}")
PY

log "run journal ready: $DB_PATH (journal_mode=wal, tables: runs, events)"

if [[ "$DB_PATH" != "$DEFAULT_DB" ]]; then
  log ""
  log "Non-default location — persist RUN_JOURNAL_DB machine-wide:"
  log "  PowerShell:  setx RUN_JOURNAL_DB \"$DB_PATH\""
  log "  bash/zsh:    echo 'export RUN_JOURNAL_DB=\"$DB_PATH\"' >> ~/.bashrc  # or your shell profile"
fi
