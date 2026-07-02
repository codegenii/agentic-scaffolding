# Sub-agent invocation contract — reference

Every Task brief inherits `.claude/agents/_task-preamble.md`. Do not paraphrase it into briefs. Beyond the preamble, every Task call must:

- Set `subagent_type` to one of `spec-reviewer`, `implementer`, `test-writer`, `pr-reviewer`.
- Spawn **without** worktree isolation — sub-agents must operate inside your worktree so their edits land where your gates check.
- **Pin the worktree path.** State your absolute worktree directory in the brief and instruct the agent to operate inside it, and give every file path as absolute, not worktree-relative. A sub-agent does not reliably inherit the driver's working directory — a brief that relies on it can run against the shared checkout instead, where the spec and branch do not exist.
- Always pass `<spec>` explicitly, as an absolute path. Briefs are the sub-agent's only context.
- Quote spec sections, test failures, and review bodies verbatim, never paraphrased.
- Never instruct a sub-agent to break a rule the preamble or its own definition enforces. Such a brief is a workflow bug — fix the brief, do not pressure the agent to comply.
