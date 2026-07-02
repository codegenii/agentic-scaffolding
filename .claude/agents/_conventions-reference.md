# Conventions reference

Detail and rationale not needed on every agent invocation. The always-applicable invariants live in `.claude/agents/_conventions.md`. Consult this file when a specific question arises — license verification, spec-authoring detail, test-structure detail.

## Specs

- Every numbered rule in a `## Behavior` section must be **testable in isolation**: a single test can confirm or refute it without relying on any other rule's side effects.
- Each rule must name the function, method, or command it constrains. A rule describing an outcome without identifying the surface is not testable.
- Rules must be falsifiable. "Returns reasonable results" is not a rule. "Returns `<NamedError>` when the input is empty" is.
- Do not reference rule numbers in code comments or test names — they drift as the spec evolves. Name the behavior directly.

Spec prose is precise, not embellished — overclaiming becomes a bad test or an unjustifiable constraint:

- **Neutral tone.** State what a unit is and does. Do not frame a missing piece as a defect ("fills the hole", "today nothing can").
- **Behavior rules are backend-agnostic.** A `## Behavior` rule must hold whatever pluggable backend is configured. A backend-specific fact is a `## Purpose` note, not a rule.
- **Out of scope, no padding.** List only what a reviewer of this spec would expect it to cover. Do not transcribe the invoker's brief.
- **Rationale is verifiable or attributable.** Every `## Design rationale` claim is checkable or names its source.

## Tests

- Table/parameterized-driven in the language's idiom: one case per scenario, named in full sentences.
- One behavior per case. Split happy path, edge case, and error condition.
- Each behavior rule maps to at least one dedicated case, traceable by the case name.
- Group related cases under named subgroups so verbose output is self-describing.
- Unit tests use injected fakes — no real services or network. Integration tests sit behind `${INTEGRATION_GATE}`.

## License

This project is released under `${LICENSE}`. Every dependency introduced must be compatible with its distribution terms.

**Allowed dependency licenses:** `${LICENSE_ALLOWLIST}`.

**Forbidden:** GPL (any version), LGPL, AGPL, SSPL, BUSL, CC-BY-SA, and any other copyleft or source-available license not in the allowlist. If a dependency's license is unknown or ambiguous, treat it as forbidden until verified.

This applies to direct and transitive dependencies. When in doubt, do not add the dependency — find a permissively-licensed alternative or implement it inline.
