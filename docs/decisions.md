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

## 3. Worker briefs carry the invariant list inline

**Context.** `invariants.md` sat 3rd–4th in every worker's warm-up read list — the position most likely skimmed as context fills. Decision 2 already caps it at 10 one-line imperatives, small enough to inline.

**Choice.** The driver reads `.claude/agents/conventions/invariants.md` once at pre-flight and pastes the invariant list verbatim into every worker brief as a stable `## Project invariants` section inside the prompt-cacheable prefix. For implementer, test-writer, and spec-writer the brief section is authoritative and the file read is a fallback; spec-reviewer and pr-reviewer still read the file. The file stays the single authoritative source — this changed delivery, not ownership.

**Why.** Content pasted into the brief gets read; a file mid-way through a load list may not. One driver read replaces a read per worker, and the stable placement keeps the section cacheable.

**Trade-off.** The list is duplicated into every brief at assembly time; an edit to `invariants.md` mid-feature does not reach briefs already assembled. Accepted knowingly.

## 4. pr-reviewer defaults to sonnet

**Context.** pr-reviewer ran on haiku on the theory that its inputs arrive
pre-validated (green tests, driver-run checks), making the review a mechanical
checklist — the same shape of theory that once put the driver on haiku
(decision 1). But its transcript is the deepest of any worker: the longest
warm-up read list (`project.md`, `_conventions.md`, `invariants.md`,
architecture index, subsystem doc), full toolchain output captured line by
line, the diff against main, and a full-file read of every changed file —
depth that scales with PR size. Decision 1 established that instruction
adherence decays with transcript depth, steeply on small models; decision 3's
inline-invariants mitigation does not cover the reviewers, so pr-reviewer
still loads `invariants.md` mid-list, the position most likely skimmed.

**Choice.** `pr-reviewer` defaults to **sonnet** (frontmatter `model:` in
`.claude/agents/pr-reviewer.md`).

**Why.** The instruction-dense work — verification tags, verdict caps,
blocking classifications, the single-call rule — executes at the end of the
transcript, at maximum depth, exactly where small-model adherence decays.
Pre-validated inputs green-light the toolchain but validate none of the five
finding sections; only license transcription is mechanical. A drifted
reviewer's characteristic failure is a false APPROVE — pass reported for a
command never run, a verdict cap forgotten — and this is the last gate before
merge. Haiku's per-review savings do not cover the cost of one false APPROVE
acted on.

**Trade-off.** Every review round costs sonnet tokens, and Phase 7 can loop
review → fix → re-review. Accepted knowingly.
