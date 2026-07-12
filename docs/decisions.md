# Design decisions

A running log of key technical and product choices, with reasoning. Written in the spirit of architecture decision records (ADRs): context, choice, alternatives, why.

<!-- Add a numbered section per decision as the project makes them. Template: -->

<!--
## 1. <Decision title>

**Context.** What forced the choice. The alternatives on the table.

**Choice.** What was decided, stated plainly.

**Why.** The reasoning. Load-bearing constraints that come out of this decision
belong in .claude/agents/conventions/invariants.md so reviewers enforce them —
this section is the reasoning, the invariant is the rule.

**Trade-off.** What this costs, accepted knowingly.
-->

## 1. Driver defaults to sonnet; the model gate is a floor

**Context.** Feature workflows drove on haiku by default, on the theory that driving is mechanical and the design thought happens in the workers. Repeated runs showed guardrail drift: by ~50% context usage haiku drivers stopped following core instructions (worktree discipline, phase gates), well before compaction. Instruction adherence decays with transcript depth, steeply on small models, and the driver holds the guardrails across the longest transcript in the system.

**Choice.** The driver defaults to **sonnet**. `use haiku` / `--haiku` is an explicit opt-down for short, shallow-transcript runs; `use opus` opts up. The gate treats the expected model as a **floor** (haiku < sonnet < opus): a session on a stronger family passes; only a weaker one is a mismatch.

**Why.** Haiku's driver-token savings do not cover the cleanup cost of one mess-on-main incident. The floor: a stronger session model is a cost choice the operator made deliberately, not a correctness risk, so an exact family match would only add friction.

**Trade-off.** Default feature runs spend more driver tokens. Accepted knowingly.

## 2. The invariant list is hard-capped at 10 one-line imperatives

**Context.** Every worker agent loads `.claude/agents/conventions/invariants.md` on every invocation, some on haiku. Instruction adherence decays with context depth, steeply on small models; each non-load-bearing line dilutes the rest and costs tokens in every run.

**Choice.** The list is capped at 10 one-line imperatives, rationale-free. Overflow moves to the matching `conventions/*.md` file. Anything a hook, lint, or CI check can enforce is implemented there instead and shrinks to at most one line naming the check. The list's own hygiene rules are stated in the file and enforced by reviewers.

**Why.** Short imperative lists survive deep contexts where long nuanced ones drift, and deterministic checks do not drift at all.

**Trade-off.** The agent-visible rule loses its nuance; this log carries it. Accepted knowingly.
