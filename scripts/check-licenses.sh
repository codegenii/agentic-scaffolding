#!/usr/bin/env bash
# Driver-run license classification for PR review (Phase 7).
#
# Deterministically classifies every direct dependency's license against the
# allowlist, so the pr-reviewer transcribes a mechanical result instead of
# resolving licenses itself — the check cannot be flubbed by a small model.
#
# Reads from .claude/project.md: ${DEP_MANIFEST} (space-separated literal
# paths), ${LICENSE_ALLOWLIST} (comma-separated license ids), and
# ${DEP_LICENSES_CMD} (a command printing one "name version license" line per
# direct dependency, or none). Values must be literal — see project.md Notes.
#
# Usage (from the repo/worktree root): ./scripts/check-licenses.sh [base-ref]
# base-ref defaults to main. The output is pasted verbatim into the
# pr-reviewer brief's "## License check" section.
#
# Exit codes: 0 — all rows allowed, dependencies unchanged, or check
# unavailable (${DEP_LICENSES_CMD} is none); 1 — at least one unknown or
# incompatible row (blocking at review); 2 — configuration error (missing or
# placeholder project.md value, failing license command) — a workflow bug,
# escalate rather than review without the check.
set -euo pipefail

PROJECT_MD=".claude/project.md"
base="${1:-main}"

fail_config() { echo "License check: config error — $1" >&2; exit 2; }

[ -f "$PROJECT_MD" ] || fail_config "$PROJECT_MD not found (run from the repo root)"

trim() { sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }

# Value cell of a ${VAR} row in a project.md table. Literal substring match on
# the full "${VAR}" token, so ${LICENSE} never collides with ${LICENSE_ALLOWLIST}.
pm_var() {
    awk -F'|' -v v="\${$1}" 'index($2, v) { print $3; exit }' "$PROJECT_MD" \
        | trim | sed -e 's/^`//' -e 's/`$//'
}

manifest="$(pm_var DEP_MANIFEST)"
allowlist="$(pm_var LICENSE_ALLOWLIST)"
licenses_cmd="$(pm_var DEP_LICENSES_CMD)"

for pair in "DEP_MANIFEST=$manifest" "LICENSE_ALLOWLIST=$allowlist" "DEP_LICENSES_CMD=$licenses_cmd"; do
    var="${pair%%=*}" value="${pair#*=}"
    [ -n "$value" ] || fail_config "\${$var} has no value in $PROJECT_MD"
    case "$value" in \<*) fail_config "\${$var} is still a placeholder in $PROJECT_MD" ;; esac
done

git rev-parse --verify --quiet "$base" >/dev/null \
    || { base="origin/$base"; git rev-parse --verify --quiet "$base" >/dev/null; } \
    || fail_config "base ref not found: ${1:-main}"

# shellcheck disable=SC2086 # manifest is a space-separated path list
if [ -z "$(git diff --name-only "$base...HEAD" -- $manifest)" ]; then
    echo "Not applicable — dependencies unchanged."
    exit 0
fi

if [ "$licenses_cmd" = "none" ]; then
    echo "Unavailable — \${DEP_LICENSES_CMD} is none in $PROJECT_MD; dependency licenses require manual verification."
    exit 0
fi

deps="$(bash -c "$licenses_cmd")" || fail_config "\${DEP_LICENSES_CMD} failed: $licenses_cmd"
[ -n "$deps" ] || fail_config "\${DEP_LICENSES_CMD} produced no output: $licenses_cmd"

# Normalize the allowlist to lowercase entries.
allowed=()
IFS=',' read -ra raw_allow <<< "$allowlist"
for a in "${raw_allow[@]}"; do
    a="$(printf '%s' "$a" | trim | tr '[:upper:]' '[:lower:]')"
    [ -n "$a" ] && allowed+=("$a")
done

# True if a license expression is satisfied: any alternative of an SPDX
# "A OR B" disjunction (licensee's choice) matching the allowlist suffices.
is_allowed() {
    local alt
    while IFS= read -r alt; do
        alt="$(printf '%s' "$alt" | trim)"
        for a in "${allowed[@]}"; do
            [ "$alt" = "$a" ] && return 0
        done
    done < <(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' \
        | sed -e 's/^(//' -e 's/)$//' | awk '{ gsub(/ or /, "\n"); print }')
    return 1
}

echo "License check vs $base — allowlist: $allowlist"
echo
echo "| dependency | version | license | verdict |"
echo "|---|---|---|---|"

n_allowed=0 n_unknown=0 n_incompatible=0
while read -r name version license; do
    [ -n "${name:-}" ] || continue
    license="$(printf '%s' "${license:-}" | trim)"
    lower="$(printf '%s' "$license" | tr '[:upper:]' '[:lower:]')"
    if [ -z "$license" ] || [ "$lower" = "unknown" ] || [ "$lower" = "unlicensed" ]; then
        verdict="unknown"; n_unknown=$((n_unknown + 1))
    elif is_allowed "$license"; then
        verdict="allowed"; n_allowed=$((n_allowed + 1))
    else
        verdict="incompatible"; n_incompatible=$((n_incompatible + 1))
    fi
    echo "| $name | ${version:-?} | ${license:-—} | $verdict |"
done <<< "$deps"

echo
echo "Summary: $n_allowed allowed, $n_unknown unknown, $n_incompatible incompatible."
[ $((n_unknown + n_incompatible)) -eq 0 ] || exit 1
