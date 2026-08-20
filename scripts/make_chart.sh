#!/usr/bin/env bash
# One-turn chart pipeline: generate -> unchanged-check -> verify --terse -> render.
#
# Collapses the three mechanical chart steps into a single tool call (fewer
# agent turns = fewer full-context resends) and short-circuits repeat
# requests: if the freshly generated chart is byte-identical to the existing
# output, the existing verified render is reused and verify/render are
# skipped entirely.
#
# Usage:
#   scripts/make_chart.sh <output.drawio> <generator.py> [generator args...]
#
# The wrapper appends `--output` itself; do not pass it. Prints <= 10 lines.
# Exit codes: 0 ok (incl. UNCHANGED), 1 generate/render failure.
# Verifier warnings do NOT fail the pipeline; they are reported in the
# summary line and the agent decides (known benign classes exist — see
# references/token-efficient-workflow.md).

set -uo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: make_chart.sh <output.drawio> <generator.py> [args...]" >&2
    exit 2
fi

OUT="$1"
GEN="$2"
shift 2
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ "$GEN" != */* ]] && GEN="$DIR/$GEN"

TMP="$(mktemp --suffix=.drawio)"
trap 'rm -f "$TMP"' EXIT

if ! python3 "$GEN" "$@" --output "$TMP"; then
    echo "GENERATE FAILED"
    exit 1
fi

if [[ -f "$OUT" ]] && cmp -s "$TMP" "$OUT"; then
    echo "UNCHANGED: $OUT is byte-identical — reusing existing verify+render"
    exit 0
fi
mv "$TMP" "$OUT"

python3 "$DIR/verify_family_tree.py" --terse "$OUT"
V=$?

if ! python3 "$DIR/flatten_export.py" "$OUT"; then
    echo "RENDER FAILED (try: docker start drawio-renderer)"
    exit 1
fi

echo "DONE (verify exit $V): $OUT"
