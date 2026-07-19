# Configuration and secrets

Secrets — connection strings, API keys, passwords, tokens — are never committed. Committed config files carry only non-secret settings; each developer supplies the real values locally, as below.

<!-- /init-project seeds this; grow it as config keys appear. This file is the
canonical guide to every config key the project reads — the coding conventions
require updating it in the same change that adds, renames, or removes a key. -->

## Quick start

<!-- The exact commands a new developer runs to supply local configuration:
local-secret-store init/set commands, `cp .env.example .env`, starting backing
services, etc. Keep it copy-pasteable. -->

## Configuration reference

Every key the project reads. Keep this table in sync when you add, rename, or remove one.

| Key | Secret | Set via |
|---|---|---|
| `RUN_JOURNAL_DB` | no | Environment variable. Path of the run-journal SQLite database. Default: `~/.agent-journal/runs.db` — machine-level, outside every checkout. Tests point it at a temp path. Local filesystem only — WAL is unsafe on network filesystems. Back up with `python -m run_journal snapshot <dest>` (never file-copy a live WAL db); restore by copying the snapshot over this path, or read one directly via `stats --db <path>`. |
| `RUN_JOURNAL_PROJECT` | no | Environment variable. Overrides the project name recorded on each run; default is derived from the nearest `.git` ancestor (worktrees resolve to the main checkout's name). |
