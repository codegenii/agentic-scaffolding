#!/usr/bin/env bash
# Driver-run exported-surface delta for PR review (Phase 7).
#
# Deterministically extracts every exported/public declaration the branch adds
# or removes, so the pr-reviewer judges the delta against the spec's Interface
# contract instead of re-deriving the export list itself.
#
# Reads from .claude/project.md: ${SOURCE_GLOB} and ${TEST_GLOB}
# (space-separated literal globs; test matches are excluded) and
# ${EXPORT_PATTERN} (a POSIX ERE matching a line that declares an
# exported/public symbol, or none). Values must be literal — see project.md
# Notes. Extraction is line-based over the diff: a moved declaration shows as
# one removed and one added line — pairing them up is reviewer judgment.
#
# Usage (from the repo/worktree root): ./scripts/surface-drift.sh [base-ref]
# base-ref defaults to main. The output is pasted verbatim into the
# pr-reviewer brief's "## Surface drift" section.
#
# Exit codes: 0 — report produced, no source changes, or check unavailable
# (${EXPORT_PATTERN} is none); 2 — configuration error (missing or placeholder
# project.md value) — a workflow bug, escalate rather than review without it.
set -euo pipefail

PROJECT_MD=".claude/project.md"
base="${1:-main}"

fail_config() { echo "Surface drift: config error — $1" >&2; exit 2; }

[ -f "$PROJECT_MD" ] || fail_config "$PROJECT_MD not found (run from the repo root)"

trim() { sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }

# Value cell of a ${VAR} row in a project.md table.
pm_var() {
    awk -F'|' -v v="\${$1}" 'index($2, v) { print $3; exit }' "$PROJECT_MD" \
        | trim | sed -e 's/^`//' -e 's/`$//'
}

src_glob="$(pm_var SOURCE_GLOB)"
test_glob="$(pm_var TEST_GLOB)"
pattern="$(pm_var EXPORT_PATTERN)"

for pair in "SOURCE_GLOB=$src_glob" "TEST_GLOB=$test_glob" "EXPORT_PATTERN=$pattern"; do
    var="${pair%%=*}" value="${pair#*=}"
    [ -n "$value" ] || fail_config "\${$var} has no value in $PROJECT_MD"
    case "$value" in \<*) fail_config "\${$var} is still a placeholder in $PROJECT_MD" ;; esac
done

if [ "$pattern" = "none" ]; then
    echo "Unavailable — \${EXPORT_PATTERN} is none in $PROJECT_MD; the exported surface requires manual comparison."
    exit 0
fi

git rev-parse --verify --quiet "$base" >/dev/null \
    || { base="origin/$base"; git rev-parse --verify --quiet "$base" >/dev/null; } \
    || fail_config "base ref not found: ${1:-main}"

pathspecs=()
for g in $src_glob; do pathspecs+=(":(glob)$g"); done
for g in $test_glob; do pathspecs+=(":(glob,exclude)$g"); done

diff_out="$(git diff "$base...HEAD" -- "${pathspecs[@]}")"
if [ -z "$diff_out" ]; then
    echo "No source changes vs $base."
    exit 0
fi

echo "Surface drift vs $base — pattern: $pattern"
echo
# Pattern travels via the environment: awk -v mangles backslash escapes.
printf '%s\n' "$diff_out" | EXPORT_PATTERN="$pattern" awk '
    BEGIN { pat = ENVIRON["EXPORT_PATTERN"] }
    /^--- (a\/|\/dev\/null)/   { ofile = $2; sub(/^a\//, "", ofile); next }
    /^\+\+\+ (b\/|\/dev\/null)/ { nfile = $2; sub(/^b\//, "", nfile); next }
    /^\+/ { line = substr($0, 2); if (line ~ pat) added   = added   "  + " nfile ": " line "\n"; next }
    /^-/  { line = substr($0, 2); if (line ~ pat) removed = removed "  - " ofile ": " line "\n"; next }
    END {
        printf "Added exported declarations:\n%s",   (added   != "" ? added   : "  (none)\n")
        printf "Removed exported declarations:\n%s", (removed != "" ? removed : "  (none)\n")
    }
'
