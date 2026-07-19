# Configuration and secrets

Secrets — connection strings, API keys, passwords, tokens — are never committed. Committed config files carry only non-secret settings; each developer supplies the real values locally, as below.

<!-- /init-project seeds this; grow it as config keys appear. This file is the
canonical guide to every config key the project reads — the coding conventions
require updating it in the same change that adds, renames, or removes a key. -->

## Quick start

Once per machine: the run journal is machine-wide, shared by every checkout
and worktree. Pick a full absolute path outside every checkout and bootstrap
it:

```bash
./scripts/init-run-journal.sh /absolute/path/runs.db
```

The script creates the database (schema, WAL mode), refuses network paths and
paths inside a checkout, and fails loudly — journal failures are otherwise
swallowed by design. Then persist the path with the `RUN_JOURNAL_DB` commands
it prints. Moving machines: see the `RUN_JOURNAL_DB` row below.

## Configuration reference

Every key the project reads. Keep this table in sync when you add, rename, or remove one.

| Key | Secret | Set via |
|---|---|---|
| `RUN_JOURNAL_DB` | no | Environment variable. Absolute path of the machine-wide run-journal SQLite database — set once per machine via `./scripts/init-run-journal.sh` (see Quick start); if unset the module falls back to `~/.agent-journal/runs.db`. Outside every checkout, local filesystem only (WAL is unsafe on network filesystems). Tests point it at a temp path. Back up with `python -m run_journal snapshot <dest>` (never file-copy a live WAL db); restore by copying the snapshot over this path, or read one directly via `stats --db <path>`. |
| `RUN_JOURNAL_PROJECT` | no | Environment variable. Overrides the project name recorded on each run; default is derived from the nearest `.git` ancestor (worktrees resolve to the main checkout's name). |
| `RUN_JOURNAL_TEMPLATE_VERSION` | no | Environment variable. Overrides the template version recorded on each run; default is the `commit` value from the checkout root's `.claude/template-version` (written by the template installer), NULL when absent. Analyze improvement across versions with `python -m run_journal stats --by-version` (filters: `--project`, `--agent`). |
