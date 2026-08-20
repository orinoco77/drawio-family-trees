#!/usr/bin/env bash
# Export a draw.io family-tree diagram to PNG without stretching.
#
# The draw.io CLI's direct PNG rasteriser has an internal canvas/texture limit.
# For very wide diagrams it renders a smaller bitmap and stretches it to the
# page size, producing an unusable elongated image. This script works around
# the bug by exporting to PDF first, then converting the PDF to PNG with
# pdftoppm.
#
# Usage:
#   scripts/export_png.sh input.drawio [output.png] [dpi]
#
# Defaults:
#   output.png -> <input basename>.png in the same directory as input.drawio
#   dpi        -> 150
#
# Requires: drawio, pdftoppm (poppler-utils)

set -euo pipefail

INPUT="${1:-}"
OUTPUT="${2:-}"
DPI="${3:-150}"

if [[ -z "$INPUT" ]]; then
    echo "Usage: $(basename "$0") input.drawio [output.png] [dpi]" >&2
    exit 1
fi

if [[ ! -f "$INPUT" ]]; then
    echo "Error: file not found: $INPUT" >&2
    exit 1
fi

if ! command -v drawio >/dev/null 2>&1; then
    echo "Error: 'drawio' not found on PATH" >&2
    exit 1
fi

if ! command -v pdftoppm >/dev/null 2>&1; then
    echo "Error: 'pdftoppm' not found on PATH (install poppler-utils)" >&2
    exit 1
fi

INPUT_DIR="$(cd "$(dirname "$INPUT")" && pwd)"
INPUT_BASE="$(basename "$INPUT")"
INPUT_ABS="$INPUT_DIR/$INPUT_BASE"
STEM="${INPUT_ABS%.drawio}"
STEM="${STEM%.dio}"

if [[ -z "$OUTPUT" ]]; then
    OUTPUT="${STEM}.png"
fi

OUTPUT_DIR="$(cd "$(dirname "$OUTPUT")" && pwd)"
OUTPUT_BASE="$(basename "$OUTPUT")"
OUTPUT_ABS="$OUTPUT_DIR/$OUTPUT_BASE"

PDF_TMP="$(mktemp --suffix=.pdf)"
trap 'rm -f "$PDF_TMP" "${PDF_TMP%.pdf}"-*.png' EXIT

echo "Exporting $INPUT_ABS to PDF..."
drawio --export --format pdf --output "$PDF_TMP" "$INPUT_ABS" >/dev/null 2>&1 || {
    echo "Error: drawio PDF export failed" >&2
    exit 1
}

echo "Converting PDF to PNG at ${DPI} DPI..."
pdftoppm -png -r "$DPI" "$PDF_TMP" "${PDF_TMP%.pdf}"

# pdftoppm names single-page output as <prefix>-1.png
PAGE_PNG="${PDF_TMP%.pdf}-1.png"

if [[ ! -f "$PAGE_PNG" ]]; then
    echo "Error: pdftoppm did not produce expected output file" >&2
    exit 1
fi

mv "$PAGE_PNG" "$OUTPUT_ABS"
echo "Wrote $OUTPUT_ABS"
