# Descendant-only layout: the missing y-position bug

## Symptom

A descendant-only chart renders as a single horizontal line: all descendants appear at the same y-coordinate, connectors seem to begin and end nowhere, and the chart is unreadable when scaled to fit a screen.

## Root cause

`generate_visitation_tree.py` uses a recursive bottom-up layout (`layout_subtree`) for `--descendants-only` charts. The function computed x-positions recursively but never assigned y-positions to child units. Children therefore retained their default `y=0`, so after the final bounding-box shift every descendant ended up on the same horizontal line.

## Fix

In `layout_subtree`, set each child unit's y-position **before** recursing into it:

```python
for c in children:
    c.y = unit.y + GENERATION_HEIGHT
child_extents = [layout_subtree(c) for c in children]
```

This ensures y propagates down the tree: root → children → grandchildren, each offset by `GENERATION_HEIGHT`.

## Follow-on issue: cramped connectors

After restoring vertical separation, the chart may still look cramped:

- Vertical child-drop lines overlap the children's name labels.
- Horizontal child connectors and marriage-line descenders crowd the parents' name labels.

This happens when the child connector sits too close to the parent text box and/or the child text box. Increase the connector padding in the child-connector layout:

```python
base_connector_y = max(max_descender_top + 20.0, unit.y + TEXT_H + 20.0)
child_y = group_infos[0]["group"][0].y
max_connector_y = base_connector_y + (len(group_infos) - 1) * CHILD_CONNECTOR_STAGGER
if max_connector_y >= child_y - 20.0 and len(group_infos) > 1:
    available = max(0.0, child_y - 20.0 - base_connector_y)
    stagger = available / (len(group_infos) - 1)
```

The `+ 20.0` padding keeps the horizontal child connector clear of both parent and child labels. Also move the marriage double-line to the bottom of the text box (`MARRIAGE_Y_OFFSET ≈ TEXT_H - 2`) so the descender starts below the parents' names, not part-way through them.

## Layout constants that produced a clean 7-generation Finigan chart

| Constant | Value | Notes |
|---|---|---|
| `TEXT_W` | 78 | Wider than compact mode; gives names room and prevents horizontal overlap |
| `TEXT_H` | 34 |  |
| `TEXT_H_SMALL` | 32 | Used for the bottom generation |
| `MARRIAGE_GAP` | 14 |  |
| `MIN_SIBLING_GAP` | 12 |  |
| `GENERATION_HEIGHT` | 110 | Tall enough for child-drop lines to clear names |
| `MARRIAGE_Y_OFFSET` | 32 | `TEXT_H - 2`; places marriage line below the label |
| `MARRIAGE_LINE_GAP` | 3 |  |
| `CHILD_CONNECTOR_STAGGER` | 6 | For multiple-spouse charts |
| Connector padding | 20 px | Above and below horizontal child connector |

## Verification

After generation, inspect the y-coordinate distribution in the `.drawio` XML. A healthy descendant chart shows one distinct y-value per generation:

```bash
python3 - <<'PY'
import xml.etree.ElementTree as ET
with open('finigan_tree.drawio') as f:
    xml = f.read()
root = ET.fromstring(xml)
ys = {}
for cell in root.iter('mxCell'):
    val = cell.get('value', '')
    geom = cell.find('mxGeometry')
    if geom is not None and val:
        y = float(geom.get('y', 0))
        ys.setdefault(y, []).append(val[:30])
for y in sorted(ys):
    print(f"y={y:8.1f}: {len(ys[y])} labels")
PY
```

If the output shows nearly all labels at one or two y-values, the recursive layout has lost vertical generational separation.

## Validator expectation

A correct descendant-only chart should validate with:

```
0 error(s), 0 warning(s)
```

Any non-zero count after the y-position fix indicates remaining geometry problems (overlapping labels, misplaced marriage lines, etc.).

## Follow-on issue: root has siblings

If the focus person has siblings in the GEDCOM, `build_tree` may collect `sibling_units` even when `--descendants-only` is set. That switches the chart into the mixed/hourglass top-down layout path, which does **not** use the recursive bottom-up `layout_subtree`. The result is a chart that has vertical generational separation but conjoins adjacent families in the middle: horizontal child connectors from different parent units overlap, child-drop lines cross into unrelated families, and the middle generations become unreadable.

### Symptom

- `validate.py` reports many warnings about overlapping `h*` / `v*` / `c*` segments.
- The rendered chart shows unrelated families (e.g. one sibling's descendants and another sibling's descendants) sharing or crossing connector lines.
- The chart width is much smaller than expected because siblings' subtrees are squeezed together instead of laid out recursively.

### Fix

Only collect sibling units when the chart actually includes ancestors (mixed/hourglass mode). In descendants-only mode, leave `sibling_units` empty so `build_tree` takes the early recursive-layout return:

```python
sibling_units = []
if include_descendants and include_ancestors:
    sibling_units = [
        FamilyUnit(
            people=[Person(s, get_name(s, individuals), get_birth(s, individuals))],
            generation=0,
            width=TEXT_W,
        )
        for s in collect_siblings(root_id, individuals, families)
    ]
```

After this change, `--descendants-only` charts always use the recursive bottom-up layout, producing the expected wide, separated subtrees and `0 error(s), 0 warning(s)`.

### Verification

After the fix, the unit count printed by the generator should equal the number of descendants of the focus person (plus the focus person), not include sibling placeholder units. The rendered chart should show clear gaps between sibling subtrees, and `validate.py` should report no warnings.

You can verify all of this with one command:

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py family_tree.drawio
```

It runs the linter, checks generational separation, and detects overlapping horizontal child connectors.
