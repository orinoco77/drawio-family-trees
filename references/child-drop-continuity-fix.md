# Child-drop continuity fix

## Problem

The vertical line dropping from a horizontal child connector to a child's name was stopped 3-4 px above the label. For an only child in the last generation, no horizontal sibling bar is drawn, so a tiny gap appeared between the parent descender and the child-drop line just above the name.

## Fix

Extend the **parent descender** (the vertical line from the parent or parent couple) by **1 px below** the horizontal child-bar. The child-drop line continues to start just below the bar and stop 3 px above the label.

- With multiple siblings, the sibling bar hides the 1 px extension.
- With one child, the extension replaces the missing sibling bar and closes the gap to the child-drop line.

Old code:
```python
parts.append(vline(f"v{h_idx}", marriage_x, descender_top, connector_y - descender_top))
...
parts.append(vline(f"c{c_idx}", blood_center(child), connector_y + 1.0, child.y - connector_y - 4.0))
```

New code:
```python
parts.append(vline(f"v{h_idx}", marriage_x, descender_top, connector_y + 1.0 - descender_top))
...
parts.append(vline(f"c{c_idx}", blood_center(child), connector_y + 1.0, child.y - connector_y - 4.0))
```

## Why not extend the child drop into the label?

Running the child drop all the way into the child's label and hiding it behind a white background rect does close the gap, but it also makes every child drop start **above** the horizontal sibling bar when siblings exist. That creates a new tiny break between the bar and the drops. Extending the parent descender by the thickness of the bar keeps sibling drops aligned below the bar while still closing the only-child gap.

## Linter updates

Update `scripts/validate.py` to ignore intentional overlaps between:
1. Child-drop lines and the horizontal connector bar at the junction
2. Child-drop lines and the vertical descender when no horizontal bar is drawn
3. Label background rects and their own text labels

See SKILL.md for the exact snippets.
