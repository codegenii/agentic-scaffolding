# Phase 3 — Add dependencies

**Entry gate:** Phase 2 exit gate passed.

Dependencies are declared in the spec and added here — before the interface skeleton — so the Phase 4 skeleton compiles against them and clears its own build gate.

Read the **External dependencies** section of `<spec>`. If the section body is "None.", the phase is a no-op — proceed to Phase 4 with no commit.

Otherwise, for each `name@version — license` line:

1. Run `${DEP_ADD_CMD}` (see `.claude/project.md`) for the dependency at the declared version.
2. Confirm the dependency appears in `${DEP_MANIFEST}` at the declared version.

After all entries are added:

- `${BUILD_CMD}` must exit 0 (skip if `none`).
- `git add ${DEP_MANIFEST} && git commit -m "chore(<unit>): add dependencies"`.

**Exit gate:** Every entry from the spec's External dependencies section appears in `${DEP_MANIFEST}` at its declared version, and `${BUILD_CMD}` exits 0. (No-op case: the section is "None." — exit gate passes immediately.)
