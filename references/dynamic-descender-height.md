# Dynamic Descender Height and Compacting a Chart

## Goal

Keep family-tree labels from overlapping connector lines while still producing a compact, book-print-ready chart. Long names wrap inside the fixed 75px label width, so a one-size-fits-all descender length either wastes space for short names or crowds tall names.

## How the generator handles it

The GEDCOM-driven generators compute a dynamic `MAX_LABEL_H` **only for the people that actually appear in the chart**:

1. `estimate_label_height(name, birth)` approximates how many lines a name will wrap into (≈14 chars per line) and returns `total_lines * 15px`.
2. `build_tree` collects the IDs of every individual that will be rendered (root, spouses, ancestors, descendants, siblings, and step-parents/step-children), finds the maximum label height in that set, and updates globals:
   - `MAX_LABEL_H` — used for all label geometry.
   - `CURRENT_GEN_H` — `DEFAULT_GENERATION_HEIGHT + (MAX_LABEL_H - DEFAULT_TEXT_H)`.
3. All hard-coded `TEXT_H` references in layout and connector code now use `MAX_LABEL_H`.

This guarantees that even the tallest label in the *chart* has enough clearance, without letting an unrelated 90px medieval-noble name elsewhere in the GEDCOM blow up the spacing of a focused tree.

## Keeping the child-name drop short

The sibling bar (horizontal child connector) is positioned by `base_connector_y`. The rule is shared across all multi-spouse generators via `scripts/drawio_layout.py:resolve_connector_y`:

```python
def resolve_connector_y(*, descender_top, max_label_h, child_y,
                        descender_offset=DESCENDER_OFFSET, child_drop=CHILD_DROP):
    parent_target = descender_top + max_label_h + descender_offset
    child_cap = child_y - child_drop
    return max(parent_target, child_cap)
```

- The bar is never lower than the parent-side minimum (`descender_top + max_label_h + DESCENDER_OFFSET`), so the parent-to-bar drop is preserved.
- The bar is never so high that the bar-to-child-name drop exceeds `CHILD_DROP`.
- `max(parent_target, child_cap)` evaluates the **lower** of the two y-values (because y grows downward), which is the visible position of the bar.

Both `generate_visitation_tree.py` and `generate_descendants_with_steps.py` call it per parent group inside the multi-spouse stagger loop, so the rule is identical across generators. `generate_line_of_descent.py` does not need it because it computes y top-down: `child_y = connector_y + CHILD_DROP` for each unit, so the bar trivially sits at the right height.

**Do not reimplement the cap at the call site.** If you find yourself writing `base_connector_y = max(..., child_y - CHILD_DROP)` at the call site, stop and call `resolve_connector_y` instead — the helper exists for exactly this rule, and reimplementing it has already produced two different bugs (the `>` vs `<` swap on the inequality, and the "raise vs lower" trap). Both generators also have their local `CHILD_DROP = 12.0` definitions removed; they import `CHILD_DROP` from `drawio_layout.py`.

### Pitfall — the "raise vs lower" trap

The natural reading of "raise the bar if the child drop is too long" is wrong. The child drop is `child_y - connector_y - 4`; if `connector_y` is too high (small y), the drop is too long. To shorten the drop, the bar has to move *down* (larger y) so the parent-to-bar drop absorbs the extra height. `resolve_connector_y` encodes this correctly: when `child_y - CHILD_DROP` exceeds `descender_top + max_label_h + DESCENDER_OFFSET`, the helper returns the larger (lower) y, which is the child-driven cap.

The equivalent failure mode is the inequality direction: getting `>` vs `<` swapped makes the cap a no-op, and the drops stay 60-px long. After any edit to `resolve_connector_y`, regenerate and check that the child-name drops are 8–12 px in the rendered PNG.

## Why the old global-max / fixed-offset approach failed

Two separate problems appeared in the Short-family session:

1. **Global max height.** Computing `MAX_LABEL_H` over the *entire* GEDCOM picked up long medieval/royal names and inflated `CURRENT_GEN_H` for a modern family chart. The fix is to compute the max only over IDs that actually appear in the rendered tree.

2. **Fixed negative offset on `base_connector_y`.** An older version used:
   ```python
   base_connector_y = max(base_connector_y, unit.y + MAX_LABEL_H + 45.0) - 40.0
   ```
   This forced the bar down relative to the parent label, which shortened the parent-to-bar drop but left a long bar-to-child drop. The symptom was a child-name drop that looked the same length as (or longer than) the parent drop. The replacement cap on `base_connector_y` relative to `child_y` fixes the symptom at the right end of the line. The current rule lives in `resolve_connector_y` and is called from both generators — do not reintroduce a fixed-offset hack at the call site.

## Rule of thumb

| Want to... | Adjust |
|------------|--------|
| Stop unrelated GEDCOM names from inflating generation spacing | Compute `MAX_LABEL_H` only from chart IDs |
| Shorten the child-name drop (sibling bar → child label) | Lower `CHILD_DROP` (or pass a smaller `child_drop` to `resolve_connector_y`) |
| Lengthen the child-name drop | Raise `CHILD_DROP` |
| Change where the line starts relative to the parent label | `descender_top` (use sparingly) |
| Scale everything with label height | `MAX_LABEL_H` / `CURRENT_GEN_H` |
| Change how big the parent-to-bar drop needs to be | `DESCENDER_OFFSET` in `drawio_layout.py` |

## Tuning the parent descender — the `DESCENDER_OFFSET` ↔ `CURRENT_GEN_H` coupling

`DESCENDER_OFFSET` controls the parent-to-sibling-bar drop, but it only
takes effect when the bar's **parent-driven target** is lower than the
**child-driven cap**:

- `parent_target = descender_top + max_label_h + DESCENDER_OFFSET`
- `child_cap = child_y - CHILD_DROP`

`resolve_connector_y` returns `max(parent_target, child_cap)`. If the
children are placed far enough below the parent that `child_cap` is the
larger of the two, the bar is pinned to the child cap and changing
`DESCENDER_OFFSET` has no visible effect on the parent descender — the
cap absorbs the change.

The size of the gap between generations is `CURRENT_GEN_H`. To make
`DESCENDER_OFFSET` actually shorten the parent descender, the children
must be placed close enough to the parent that the parent-driven target
wins, i.e.:

```
child_y - CHILD_DROP  <=  descender_top + max_label_h + DESCENDER_OFFSET
```

which simplifies to:

```
CURRENT_GEN_H  <=  MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1
                  + max_label_h + DESCENDER_OFFSET + CHILD_DROP
```

The shared `drawio_layout.min_generation_height(max_label_h)` returns
exactly that right-hand side plus a small `INTER_GEN_GAP` for breathing
room. **Both generators now set `CURRENT_GEN_H = min_generation_height(MAX_LABEL_H)`.**
The previous legacy formula `DEFAULT_GENERATION_HEIGHT + (MAX_LABEL_H - DEFAULT_TEXT_H)`
(165 px for 90 px labels) was too large: it pinned the bar at the child
cap regardless of `DESCENDER_OFFSET`, so reducing `DESCENDER_OFFSET` from
40 to 15 alone did nothing to the parent descender. The fix is to use
`min_generation_height` so the parent-driven target is binding.

If you ever raise `DESCENDER_OFFSET` and want the parent descender to
actually grow, you must also raise `CURRENT_GEN_H` (or `INTER_GEN_GAP`)
so the chart still has room for the children. Edit only `drawio_layout.py`
— never re-implement the formula at the call site.

## Verification

After any geometry change, regenerate the chart and run:

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py chart.drawio
```

Do not treat the chart as fixed until it reports `0 error(s), 0 warning(s)`. Then visually inspect the rendered PNG/SVG, because the linter does not catch every crowding artefact. A quick sanity check the linter *does* catch: parse the rendered `.drawio` and compute the actual drop heights from the `c*` vertical rect cells. They should be 8–12 px; numbers above 20 px mean `resolve_connector_y` is not being called or has the wrong inequality.
