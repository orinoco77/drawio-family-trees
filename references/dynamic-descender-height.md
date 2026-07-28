# Dynamic Descender Height and Compacting a Chart

## Goal

Keep family-tree labels from overlapping connector lines while still producing a compact, book-print-ready chart. Long names wrap inside the fixed 75px label width, so a one-size-fits-all descender length either wastes space for short names or crowds tall names.

## How the generator handles it

`generate_descendants_with_steps.py` computes a dynamic `MAX_LABEL_H` **only for the people that actually appear in the chart**:

1. `estimate_label_height(name, birth)` approximates how many lines a name will wrap into (≈14 chars per line) and returns `total_lines * 15px`.
2. `build_tree` collects the IDs of every individual that will be rendered (root, spouses, ancestors, descendants, siblings, and step-parents/step-children), finds the maximum label height in that set, and updates globals:
   - `MAX_LABEL_H` — used for all label geometry.
   - `CURRENT_GEN_H` — `DEFAULT_GENERATION_HEIGHT + (MAX_LABEL_H - DEFAULT_TEXT_H)`.
3. All hard-coded `TEXT_H` references in layout and connector code now use `MAX_LABEL_H`.

This guarantees that even the tallest label in the *chart* has enough clearance, without letting an unrelated 90px medieval-noble name elsewhere in the GEDCOM blow up the spacing of a focused tree.

## Keeping the child-name drop short

The sibling bar (horizontal child connector) is positioned by `base_connector_y`. The code first computes a minimum height from the parent side:

```python
desired_lengths = [45.0 if gi["is_single"] else 63.0 for gi in group_infos]
base_connector_y = max(
    gi["descender_top"] + length
    for gi, length in zip(group_infos, desired_lengths)
)
```

Then it raises the bar if that would leave too long a drop down to the child names:

```python
MAX_CHILD_NAME_DROP = 22.0
base_connector_y = max(
    base_connector_y,
    child_y - MAX_CHILD_NAME_DROP - 4.0,
    unit.y + MAX_LABEL_H + 8.0,
)
```

- `base_connector_y` is never lower than the parent-side minimum, so the parent-to-bar drop is preserved.
- It is never so high that the bar-to-child-name drop exceeds `MAX_CHILD_NAME_DROP`.
- It stays clear of the parent label (`unit.y + MAX_LABEL_H + 8.0`).

## Why the old global-max / fixed-offset approach failed

Two separate problems appeared in the Short-family session:

1. **Global max height.** Computing `MAX_LABEL_H` over the *entire* GEDCOM picked up long medieval/royal names and inflated `CURRENT_GEN_H` for a modern family chart. The fix is to compute the max only over IDs that actually appear in the rendered tree.

2. **Fixed negative offset on `base_connector_y`.** The older code used:
   ```python
   base_connector_y = max(base_connector_y, unit.y + MAX_LABEL_H + 45.0) - 40.0
   ```
   This forced the bar down relative to the parent label, which shortened the parent-to-bar drop but left a long bar-to-child drop. The symptom was a child-name drop that looked the same length as (or longer than) the parent drop. Capping the bar relative to `child_y` instead fixes the symptom at the right end of the line.

## Rule of thumb

| Want to... | Adjust |
|------------|--------|
| Stop unrelated GEDCOM names from inflating generation spacing | Compute `MAX_LABEL_H` only from chart IDs |
| Shorten the drop from the sibling bar to child names | Lower `MAX_CHILD_NAME_DROP` (or cap `base_connector_y` closer to `child_y`) |
| Lengthen the drop from the sibling bar to child names | Raise `MAX_CHILD_NAME_DROP` |
| Change where the line starts relative to the parent label | `descender_top` (use sparingly) |
| Scale everything with label height | `MAX_LABEL_H` / `CURRENT_GEN_H` |

## Verification

After any geometry change, regenerate the chart and run:

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py chart.drawio
```

Do not treat the chart as fixed until it reports `0 error(s), 0 warning(s)`. Then visually inspect the rendered PNG/SVG, because the linter does not catch every crowding artefact.
