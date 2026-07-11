# Spec conventions (spec-writer, spec-reviewer)

Prose rules for feature specs. spec-writer writes each spec to these rules (Phase 1); spec-reviewer enforces them.

## Behavior rules

- Every numbered rule in a `## Behavior` section must be **testable in isolation**: a single test can confirm or refute it without relying on any other rule's side effects.
- Each rule must name the function, method, or command it constrains. A rule describing an outcome without identifying the surface is not testable.
- Rules must be falsifiable. "Returns reasonable results" is not a rule. "Returns `<NamedError>` when the input is empty" is.
- Do not reference rule numbers in code comments or test names — they drift as the spec evolves. Name the behavior directly.

## Prose precision

Spec prose is precise, not embellished — overclaiming becomes a bad test or an unjustifiable constraint:

- **Neutral tone.** State what a unit is and does. Do not frame a missing piece as a defect ("fills the hole", "today nothing can").
- **Behavior rules are backend-agnostic.** A `## Behavior` rule must hold whatever pluggable backend is configured. A backend-specific fact is a `## Purpose` note, not a rule.
- **Out of scope, no padding.** List only what a reviewer of this spec would expect it to cover. Do not transcribe the invoker's brief.
- **Rationale is verifiable or attributable.** Every `## Design rationale` claim is checkable or names its source.
