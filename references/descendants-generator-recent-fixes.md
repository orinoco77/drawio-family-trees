# Recent fixes to `generate_descendants_with_steps.py`

This note captures the state of the extended descendant generator after the July 2026 Short/Finigan chart work. The generator script itself is the source of truth; this file records *why* the current behaviour is what it is and gives copy/paste command patterns.

## Working command patterns

### Focused descendant chart with step-children

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_descendants_with_steps.py \
  --gedcom "/path/to/tree.ged" \
  --root "Brian Stanley Short" \
  --generations 3 \
  --descendants-only \
  --include-step-children \
  --title "Shorts of Wigan" \
  --font-family "Times New Roman" \
  --output brian_short_descendants.drawio
```

- `--descendants-only` is required if you do **not** want ancestors above the root.
- `--include-step-children` adds spouses' previous partners as additional spouses and includes their children.
- `--title` and `--font-family` apply to the whole diagram.

### All descendants of a historical root, by ID

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_descendants_with_steps.py \
  --gedcom "/path/to/tree.ged" \
  --root-id "@I18915667319@" \
  --all-descendants \
  --descendants-only \
  --output thomas_finigan_1820_descendants.drawio
```

- Use `--root-id` when the name is ambiguous or the user gives a birth year.
- `--all-descendants` auto-detects the deepest blood-descendant generation. It does **not** see deeper step-children branches; if you need those, specify `--generations N` explicitly with `--include-step-children`.

### Render and verify

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/flatten_export.py family_tree.drawio --png
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py family_tree.drawio
```

## Code-level fixes now in place

1. **Dynamic height uses only people in the chart.** `MAX_LABEL_H` and `CURRENT_GEN_H` are computed from the IDs that actually appear, not from the whole GEDCOM. This prevents one unrelated medieval noble with a 90 px tall name from inflating a focused 20th-century tree.

2. **Short child-name drops.** `base_connector_y` is raised so the vertical drop from the horizontal sibling bar down to each child name stays around `MAX_CHILD_NAME_DROP` px (currently 22). The parent-to-bar drop absorbs the extra vertical room instead.

3. **Step-parent marriage lines are always drawn.** A step-parent is married to the blood person's current spouse, not to the blood person. The marriage indicator is drawn regardless of whether that marriage produced children who appear in the chart.

4. **Non-descendant multiple-spouse pair logic is a star, not a chain.** For a non-descendant unit `[S1, Blood, S2, S3, ...]`, marriage pairs are `(S1, Blood)`, `(S1, S2)`, `(S1, S3)`, etc. Previously pairs were chained `(S1,Blood), (Blood,S2), (S2,S3)`, which wrongly implied S2 and S3 were married.

5. **Overlapping marriage lines share the same y-coordinate.** In descendant units with multiple spouses all to the right, the marriage lines share the blood person's right edge and overlap geometrically. They are all drawn at the same `MARRIAGE_Y_OFFSET` y-coordinate. Duplicate segments simply overlay the first line; the labels are drawn on top with a white background, so the result looks like a single continuous line to the farthest spouse. Do **not** stagger these lines vertically — either upward or downward — because that produces misaligned indicators (one marriage line visibly higher than another, or a line that appears to run between two unrelated spouses) and can collide with child descenders.

## Visual symptom: one marriage indicator looks doubled or sits too high

When a blood person has multiple spouses drawn to the right (descendant layout), each marriage indicator starts at the blood person's right edge and runs to that spouse's left edge. Because they share the same starting x, the shorter lines are completely covered by the longest line. If the code staggers those overlapping lines vertically — even by a few pixels — the user sees:

- a **doubled** vertical segment where two indicators overlap at different y values (e.g. between Olivia O'Keeffe and Douglas Clarke-Letton), and
- a **spurious line that looks too high** where the longer indicator extends past an intermediate spouse toward a farther spouse (e.g. a line appearing between Douglas Clarke-Letton and Michael Jones).

**Fix:** remove the vertical offset. Draw every overlapping marriage indicator at the same `MARRIAGE_Y_OFFSET` y-coordinate. Duplicate segments overlay exactly, labels are drawn on top with a white background, and the rendered image shows a single continuous line. Offsetting upward hides lines behind labels but still triggers linter warnings; offsetting downward collides with child descenders.

## Interpreting `verify_family_tree.py` output

- **Connector overlaps between different family units** (`h*`/`v*`/`c*` from unrelated marriages crossing) are real defects.
- **Marriage-line-to-label overlap warnings** are expected and harmless. The marriage lines are deliberately drawn behind white-filled labels.
- A chart reporting **0 errors, OK connector check**, and only marriage-line-under-label warnings is safe to deliver.
- If the validator is rerun repeatedly without visible improvement, stop chasing warnings and **show the rendered image** to the user for human verification.
