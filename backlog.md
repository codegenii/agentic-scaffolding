# Improvement backlog — template development only

Deferred structural improvements, each as a self-contained prompt to run in a fresh session against this repo. Not part of the template: `/init-project` deletes this file.

## 1. Repo-wide markdownlint pass + config

> Phases 4–7 and `orchestrator.md`'s worker brief template are markdownlint-clean in their brief content (2026-07-11); the rest of the template still carries the original violations: bare `<placeholder>` tokens in phase 1's spec template (MD033), unlanguaged fences in CONTRIBUTING and bootstrap-guide (MD040), compact table pipes repo-wide (MD060), and missing blank lines around lists/headings in several files (including the phase files' entry/exit gates). Sweep all markdown to those conventions and add a `.markdownlint.jsonc` recording the chosen rule set and table style. The `## Extracted ...` headings the worker brief template emits are a load-bearing contract the agents match on — never rename them. Content-neutral: no wording changes, only formatting.
