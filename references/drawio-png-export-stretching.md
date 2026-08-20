# draw.io CLI direct PNG export stretches wide charts

## Symptom

After generating a wide family-tree `.drawio` file, running:

```bash
drawio --export --format png --output chart.png chart.drawio
```

produces a PNG whose dimensions match the page size (e.g. 8199 × 694) but the
content looks like a small slice of the top-left corner blown up to fill the
canvas. Text and lines are horizontally elongated and unreadable.

## Cause

The draw.io CLI's direct PNG rasteriser has an internal texture/canvas size
limit. When the diagram is wider than that limit, it renders a smaller internal
bitmap and stretches it to the requested output dimensions. Exporting the same
file to SVG or PDF is not affected because both remain vector formats.

## Workaround

Export to PDF first, then convert the PDF to PNG with `pdftoppm`:

```bash
drawio --export --format pdf --output chart.pdf chart.drawio
pdftoppm -png -r 150 chart.pdf chart
mv chart-1.png chart.png
```

Or use the skill's helper script:

```bash
scripts/export_png.sh chart.drawio chart.png 150
```

The script requires `drawio` and `pdftoppm` (poppler-utils) on PATH.

## Choosing DPI

- `100` — smaller file, fine for screen review
- `150` — good balance for print-ready output (default)
- `200` or higher — large file, use only for high-resolution print

## Verification

After conversion, the PNG should show the full width of the family tree with
consistent, non-stretched text. Check the aspect ratio: it should be roughly the
same as the `.drawio` page size (`pageWidth / pageHeight`). If it is drastically
different, the direct PNG export path is still being used.
