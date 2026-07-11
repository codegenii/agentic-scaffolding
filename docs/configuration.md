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
| <!-- first key lands here --> | | |
