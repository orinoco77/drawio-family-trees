# Pre-delivery checklist for generated family trees

Run these checks before presenting a generated family tree to the user. A chart that fails any check must not be delivered.

## 1. Generate with the right mode

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_visitation_tree.py \
    --gedcom "family.ged" \
    --root-id "@I123@" \
    --all-descendants \
    --descendants-only \
    --output tree.drawio
```

For an ancestor chart, use `generate_ancestor_tree_recursive.py`, not the visitation generator in ancestor-only mode.

## 2. Render to PNG/SVG

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/flatten_export.py tree.drawio
```

If the PNG is 0 bytes, the renderer timed out. Fall back to `scale=1` or use the SVG/drawio source.

## 3. Run the pre-delivery verifier

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py tree.drawio
```

Expected output:

```
1. Structural linter
   OK: 0 error(s), 0 warning(s)

2. Generational separation
   Distinct label y-values: <expected number of generations>

3. Connector overlap check
   OK: no overlapping horizontal child connectors

All checks passed. The chart is safe to deliver.
```

Do not deliver if any check fails.

## 4. Visually inspect the rendered image

The linter and verifier catch geometry errors, not aesthetic problems. Open the PNG (or a cropped section) and check:

- Marriage lines sit at the visual centre/baseline of spouse labels.
- Vertical descenders look continuous from marriage line to child connector.
- Child names are not crowded by the sibling bar above them.
- Different families are visibly separated; no connector lines cross into unrelated branches.
- For very wide charts, names remain readable in the source SVG/drawio even if the PNG preview is downscaled.

If vision tools cannot render the image, crop the affected region with PIL and inspect the pixels. See `references/visual-verification.md`.

## 5. Deliver the right formats

Always attach all three:

- `.drawio` — editable source
- `.svg` — zoomable vector preview
- `.png` — quick raster preview

For wide all-descendant charts, tell the user that the `.drawio` and `.svg` are the readable versions. See `references/descendant-chart-delivery.md`.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| All labels at same y-value | Recursive descendant layout lost y-positioning | See `references/descendant-layout-y-position-bug.md` |
| Families conjoined, crossed lines, many validator warnings | Root has siblings and mixed-mode layout was used for descendants-only | See "Root has siblings" in `references/descendant-layout-y-position-bug.md` |
| Missing vertical lines in PNG export | Renderer ignored `direction=south` on `shape=line` | Already handled by generator using `shape=rect` for verticals |
| PNG transparent background | Export did not set `bg=#FFFFFF` | `flatten_export.py` injects white background |
