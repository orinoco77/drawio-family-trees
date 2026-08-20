# Pre-delivery checklist for generated family trees

Run these checks before presenting a generated family tree to the user. A chart that fails any check must not be delivered.

**Output location:** save all generated charts to `/home/tv/family tree charts/`
(quote the path because of the space). See `references/workflow-conventions.md`.

## 1. Generate with the right mode

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_visitation_tree.py \
    --gedcom "family.ged" \
    --root-id "@I123@" \
    --all-descendants \
    --output "/home/tv/family tree charts/tree.drawio"
```

For an ancestor chart, use `generate_ancestor_tree_recursive.py`, not the visitation generator in ancestor-only mode.

## 2. Render to PNG/SVG

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/flatten_export.py tree.drawio
```

If the PNG is 0 bytes, the renderer timed out. Fall back to `scale=1` or use the SVG/drawio source.

**If `flatten_export.py` itself fails (online drawio export service unavailable):**

The `drawio` CLI binary at `/usr/bin/drawio` can render locally without going through the online service:

```bash
drawio --export --format svg --output tree.svg tree.drawio
```

For PNG, do **not** call `drawio --export --format png` directly on wide charts.
The draw.io CLI rasteriser has an internal texture/canvas limit; very wide diagrams
are rendered as a small slice and stretched to the page size, producing an unusable
elongated image. Instead use the skill's helper:

```bash
~/.hermes/skills/drawio-family-trees/scripts/export_png.sh \
    "/home/tv/family tree charts/tree.drawio" \
    "/home/tv/family tree charts/tree.png" 150
```

Run SVG export and `export_png.sh` in parallel (`&` + `wait`) to halve wall time.
Output dimensions can be checked with `file tree.png` (returns `PNG image data,
<width> x <height>, ...`).

## 3. Run the pre-delivery verifier

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py \
    "/home/tv/family tree charts/tree.drawio"
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

**When the user reports the chart "looks wrong" but the validator passes clean, the chart is broken.** Do not retry the validator; render and inspect the image. The validator only catches:
- malformed edges (cells with non-positive dimensions, missing geometry)
- connector overlap at the same y-coordinate (sibling bars crossing)
- generations at the same y-coordinate

It does **not** catch:
- descenders landing next to the wrong name box
- spouses in the wrong order (`[Blood, S1, S2]` when they should be `[S1, Blood, S2]`)
- families visually merged because two distinct marriage lines share a descender
- connector lines crossing into unrelated branches across different generations
- negative-height drop segments where the algorithm thought a child was above its parent

If the user says "the chart is wrong" and the linter is silent, the fastest fix is to render the PNG/SVG and look at it. **Skip the validator output entirely** — repeating it will not change the answer.

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
