# Configuration and secrets

Secrets — connection strings, API keys, passwords, tokens — are never committed. Committed config files carry only non-secret settings; each developer supplies the real values locally, as below.

<!-- /init-project seeds this; grow it as config keys appear. This file is the
canonical guide to every config key the project reads — the coding conventions
require updating it in the same change that adds, renames, or removes a key. -->

## Quick start

One-time per machine, before the first journaled run — create the run-journal
database eagerly and fail loudly (journal failures are otherwise swallowed by
design, so a broken path would record nothing, silently):

```bash
./scripts/init-run-journal.sh                      # default: ~/.agent-journal/runs.db
./scripts/init-run-journal.sh /custom/dir/runs.db  # custom location
```

The script refuses network paths (WAL is unsafe there) and paths inside a
checkout (the journal is machine-level), verifies schema and WAL mode, and is
safe to re-run. Skipping it is safe too: the first journal call bootstraps the
same way, just without the loud failure.

With a custom location, persist `RUN_JOURNAL_DB` machine-wide — the script
prints the exact commands (`setx RUN_JOURNAL_DB "<path>"` in PowerShell, or an
`export` line in your shell profile). Moving to another machine: see the
`RUN_JOURNAL_DB` row below for snapshot/restore.

## Configuration reference

Every key the project reads. Keep this table in sync when you add, rename, or remove one.

| Key | Secret | Set via |
|---|---|---|
| `RUN_JOURNAL_DB` | no | Environment variable. Path of the run-journal SQLite database. Default: `~/.agent-journal/runs.db` — machine-level, outside every checkout. Tests point it at a temp path. First run on a machine: `./scripts/init-run-journal.sh` (see Quick start). Local filesystem only — WAL is unsafe on network filesystems. Back up with `python -m run_journal snapshot <dest>` (never file-copy a live WAL db); restore by copying the snapshot over this path, or read one directly via `stats --db <path>`. |
| `RUN_JOURNAL_PROJECT` | no | Environment variable. Overrides the project name recorded on each run; default is derived from the nearest `.git` ancestor (worktrees resolve to the main checkout's name). |
