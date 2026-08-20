# Line-of-descent chart with siblings

A narrow descendant chart that sits between a direct-line pedigree and a full descendants tree.

## When to use

The user wants to see the **immediate family context** around a chosen bloodline without bringing in every descendant. For each ancestor on the line, draw that ancestor, their spouse, and **all children of that marriage**. Only the child who continues the line is expanded further; siblings appear as names only.

Example use-case: show Alexander Douglas Short → William Short → Alexander William Walter Short → Brian Stanley Short, including William's siblings, Alexander William Walter's siblings, and Brian's siblings, but not the descendants of those siblings.

## Generator

`scripts/generate_line_of_descent.py`

```bash
python3 scripts/generate_line_of_descent.py \\
  --gedcom "family.ged" \\
  --line "@I18912185984@,@I18910653723@,@I18910597060@,@I18910553828@" \\
  --title "Line of descent: Alexander Douglas Short to Brian Stanley Short" \\
  --font-family "Times New Roman" \\
  --output line_of_descent.drawio
```

- `--line` — comma-separated `@I...@` IDs from the top ancestor down to the target person. At least two IDs are required.
- `--title`, `--font-family`, `--output` — same conventions as the other generators.

The generator imports layout constants and helpers from `scripts/drawio_layout.py` so it follows the same rules as `generate_visitation_tree.py` and `generate_descendants_with_steps.py`.

## Algorithm

1. Validate that each successive ID in `--line` is a child of the previous ID in some GEDCOM family.
2. For each ancestor (except the target), build a family unit from the marriage that produced the next person in the line.
3. Compute a local horizontal layout: ancestor left, spouse right, children centred under the couple.
4. Make room for the next unit's spouse to the right of the line child.
5. Compute horizontal offsets bottom-up so each line child lines up with the ancestor label in the unit below, then shift the whole diagram so the leftmost element has a comfortable margin.
6. Compute y positions **top-down**:
   - The top ancestor unit starts at `root_y = MARGIN + TITLE_Y + 20`.
   - For each unit, compute the sibling-bar y (`connector_y`) from the parent side.
   - Compute the child-label y from the sibling bar: `child_y = connector_y + CHILD_DROP`.
   - The line child (who continues the line) becomes the root of the next unit at `root_y = child_y`.

This top-down flow means child labels are positioned **relative to the sibling bar**, not to the parent labels. Raising or lowering the bar raises or lowers the children with it, so the sibling-bar-to-child-name drop stays short and constant.

## Layout constants

The generator imports the following from `scripts/drawio_layout.py`:

- `TEXT_W = 75`, `DEFAULT_TEXT_H = 30`
- `MARRIAGE_GAP = 14`, `MARRIAGE_Y_OFFSET = 18`, `MARRIAGE_LINE_GAP = 3`
- `SIBLING_GAP = 12`
- `DEFAULT_GENERATION_HEIGHT = 105`
- `CHILD_DROP = 12`
- `DESCENDER_OFFSET = 40`

## Dynamic vertical spacing

To prevent wrapped labels from overlapping connector lines, the generator computes the maximum label height (`MAX_LABEL_H`) **among the people actually appearing in the chart**. Label height is estimated with `estimate_label_height()`, which assumes ~14 characters per wrapped line.

This is the same adaptive-height strategy used by `generate_visitation_tree.py` and `generate_descendants_with_steps.py`, but the line-of-descent generator does not use a fixed `CURRENT_GEN_H`. Instead, each generation's height is determined by the sibling-bar position, which depends on `MAX_LABEL_H`.

## Descender and child-drop geometry

For each unit:

- `marriage_line_bottom = root_y + MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1.0`
- For couples the vertical descender starts at `marriage_line_bottom`; for single parents it starts at `root_y + MAX_LABEL_H`.
- Target parent-to-sibling-bar drop:

  ```python
  desired_parent_drop = MAX_LABEL_H + DESCENDER_OFFSET  # text-box length + 40 px
  connector_y = descender_top + desired_parent_drop
  ```

  This gives the approximately -40 px descender offset (text-box length minus drop length) used across the drawio-family-trees generators.

- The sibling bar is capped so the child-name drop stays short:

  ```python
  connector_y = min(connector_y, child_y - CHILD_DROP)
  ```

  With this cap the bar is always `CHILD_DROP` (12 px) above the child labels.

- Child labels are positioned from the sibling bar:

  ```python
  child_y = connector_y + CHILD_DROP
  ```

- Each child drop runs from `connector_y + 1.0` down to `child_y - 4.0`, matching the descendant generators:

  ```python
  drop_h = child_y - connector_y - 4.0  # = CHILD_DROP - 4.0 = 8 px
  ```

## Draw order

All connector lines (marriage lines, descenders, horizontal child connectors, and child drops) are emitted **before** the person labels. Every label has a white background rect, so drawing labels on top hides any intentional line segments that pass through the label's bounding box. This is what makes wrapped-label charts readable and overlap-free.

## Verification

Run the standard checker:

```bash
python3 scripts/verify_family_tree.py line_of_descent.drawio
```

Expected result: `0 error(s), 0 warning(s)`. The structural linter will object if the vertical descender overlaps the horizontal child connector, so the generator stops the descender at `connector_y` and starts child drops at `connector_y + 1.0`.

## Limitations

- Only the marriage that produces the next person in the line is shown. If an ancestor had multiple marriages, the others are omitted.
- The target person appears as a child in the final unit; their own spouse and children are not drawn unless the user explicitly asks for them.
- Large sibling groups can still make the chart wide, but it remains much smaller than a full all-descendants chart.

## Pitfalls

### Missing sibling labels

The most common implementation mistake is drawing vertical child drops for every sibling while forgetting to emit the actual text labels. The result looks like couples with dangling descenders but no children. This is especially obvious at the bottom of the chart, where the target person appears to be absent even though the line descends to their position.

**Fix:** emit a `text` cell for every child. Skip the child-level label only for intermediate line children, because the next unit down draws that person as an adult. The final target person *must* be drawn as a child label in the last unit.

### Duplicate labels for intermediate line children

If both the child loop and the next unit emit a label for the same line child, the two labels overlap exactly. Avoid this by drawing the child label only when the child is not continued in the next unit.

### Sibling labels colliding with the next unit's spouse

Because each unit's children are centred under its couple but the next unit is anchored on the line child, siblings to the right of the line child can end up at the same y-coordinate as (and horizontally overlapping) the next unit's spouse label. The linter reports this as label-to-label overlap, not the acceptable marriage-line-under-label case.

**Fix:** after computing the local child positions for a unit (except the last), ensure the gap between the line child and the next sibling is wide enough to fit the next unit's spouse label plus the normal sibling gap. If it is not, push all siblings to the right of the line child rightward by the shortfall before the bottom-up offset pass. This may slightly de-centre the children under their parents, but it keeps every generation readable and overlap-free.

In `generate_line_of_descent.py` this is implemented by `ensure_spouse_room()` and applied to each unit before offsets are computed.

### Text/line overlap from long wrapped labels

A fixed generation height and fixed descender start will eventually cut through a multi-line name (e.g. "Alexander William Walter Short" wraps to three lines). If lines are drawn after labels, the overlap is visible; if labels are drawn after lines, the white label background hides it.

**Fix:**
1. Compute `MAX_LABEL_H` from everyone who appears in the chart.
2. Start the vertical descender below the tallest label (`root_y + MAX_LABEL_H + 1.0` for single parents, or at `marriage_line_bottom` for couples, which is hidden behind the label anyway).
3. Emit all connector lines before person labels so label backgrounds cover any geometry that passes through the text box.

### Child-name drops that are too long (or too short)

If the sibling bar is positioned too far above the child labels, the short vertical drops become long vertical lines that dominate the chart. If the bar is too close to the child labels, the drops become tiny ticks that look broken.

**Fix:** position the child labels relative to the sibling bar (`child_y = connector_y + CHILD_DROP`) rather than at a fixed generation height. This keeps the drop length constant and independent of the parent-to-bar drop. Then tune `CHILD_DROP` in `drawio_layout.py` if a different drop length is needed.

### Forgetting that child labels move with the sibling bar

When adjusting the parent-to-sibling-bar drop (e.g. to change the -40 px offset), it is easy to leave `child_y` fixed relative to the parent labels. That stretches or shrinks the child-name drop and can either create overlap with parent labels or make the drops look wrong.

**Fix:** compute `child_y` from `connector_y`, not from `root_y`. In the line-of-descent generator this means processing units top-down and setting `root_y_{i+1} = child_y_i`.
