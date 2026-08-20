# Recent fixes to `generate_descendants_with_steps.py`

This note captures the state of the extended descendant generator after the July 2026 Short/Finigan chart work. The generator script itself is the source of truth; this file records *why* the current behaviour is what it is and gives copy/paste command patterns.

## Working command patterns

`generate_descendants_with_steps.py` defaults to **descendants-only**.
`--descendants-only` has been removed; use `--ancestors-only` for ancestor-only
mode.

### Focused descendant chart with step-children

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_descendants_with_steps.py \
  --gedcom "/path/to/tree.ged" \
  --root "Brian Stanley Short" \
  --generations 3 \
  --include-step-children \
  --title "Shorts of Wigan" \
  --font-family "Times New Roman" \
  --output brian_short_descendants.drawio
```

- `--include-step-children` adds spouses' previous partners as additional spouses and includes their children.
- `--title` and `--font-family` apply to the whole diagram.

### All descendants of a historical root, by ID

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_descendants_with_steps.py \
  --gedcom "/path/to/tree.ged" \
  --root-id "@I18915667319@" \
  --all-descendants \
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

6. **`_apply_unit_x` always uses `[S1, Blood, S2, ...]` regardless of descendant status.** Previously `_apply_unit_x` had a `elif unit.people[0].is_descendant:` branch that laid out descendants with all spouses to the right (`[Blood, S1, S2, ...]`), contradicting `place_unit_at_blood_center` which uses `[S1, Blood, S2]` for two-spouse units. When `_resolve_overlaps` called `_apply_unit_x` after `layout_subtree`, descendants ended up with the blood person on the LEFT and the first spouse in the MIDDLE, so a marriage-line descender landed visually next to a different name box and looked like it was "coming from the wrong person's box". The fix removes the descendant branch from `_apply_unit_x` and uses the same `[S1, Blood, S2, ...]` layout as `place_unit_at_blood_center`. **Rule for future scripts:** if a generator has both `_apply_unit_x` and `place_unit_at_blood_center`, they must use the **same** spouse-order convention. If you need descendant-specific layout, put it in `place_unit_at_blood_center`'s `all_spouses_right` parameter and have `_apply_unit_x` compute the same result from `unit.center`.

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

## Additional fixes (late July 2026)

7. **Single-parent child groups are no longer offset sideways.** In `layout_subtree`, child groups for `spouse_idx == 0` (no spouse / single parent) now use offset `0.0`, so the child stays centred under the blood parent instead of being shifted by a marriage-gap multiple.

8. **Multi-spouse child-connector stagger restored.** A guard in the stagger loop compared `base_connector_y + stagger` to the same `base_connector_y`, reducing the stagger to zero for every multi-spouse parent. The guard was removed; the rightmost spouse's children again sit highest and each subsequent spouse's connector steps down by `CHILD_CONNECTOR_STAGGER`.

9. **Only child with a spouse stays centred under the parent.** The layout used the group's geometric centre `(left + right) / 2` as the alignment point. For a single child with a spouse, that midpoint is shifted toward the spouse, so the blood child moved left and the parent connector entered the side of the name. The alignment point is now the **blood-centre midpoint** of the children, matching `layout_children`. See `references/only-child-with-spouse-alignment.md`.

10. **Wide-chart PNG export via PDF.** The draw.io CLI's direct PNG rasteriser stretches very wide diagrams. Use `scripts/export_png.sh chart.drawio chart.png 150` (PDF → `pdftoppm`) for clean output. See `references/drawio-png-export-stretching.md`.

## Do not run in mixed (hourglass) mode

`generate_descendants_with_steps.py` supports two modes:

- **Default** — descendants only.
- `--ancestors-only` — ancestors only.

Running it without either flag on a root with siblings produces a mixed/hourglass
chart, but the mixed-mode connector code collides with the pre-existing
sibling-bar overlap bug and generates many more overlapping connector pairs than
descendants-only mode. For hourglass charts, use `generate_visitation_tree.py`
instead.
