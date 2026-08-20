# Connector geometry (shared `drawio_layout.py`)

All generators MUST route connector y-positions through these helpers so
the charts share a single set of spacing rules.

## Constants

| Symbol | Value | Used for |
|---|---|---|
| `MARGRIAGE_Y_OFFSET` | 18.0 | Distance from parent top to upper marriage line |
| `MARRIAGE_LINE_GAP` | 3.0 | Vertical gap between the two marriage lines |
| `CHILD_DROP` | 12.0 | Distance from sibling bar down to child label top |
| `DESCENDER_OFFSET` | 40.0 | Added to (descender_top + max_label_h) for the parent-driven sibling bar target |

## Helpers

```python
from drawio_layout import (
    descender_top_couple, descender_top_single,
    connector_y_from_parent, connector_y_from_child,
    child_y_from_connector, resolve_connector_y,
)
```

- `couple_descender_top(root_y)` → `root_y + MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1.0`
- `single_descender_top(root_y, max_label_h)` → `root_y + max_label_h`
- `connector_y_from_parent(descender_top, max_label_h, offset=DESCENDER_OFFSET)` → `descender_top + max_label_h + offset`
- `connector_y_from_child(child_y, drop=CHILD_DROP)` → `child_y - drop`
- `child_y_from_connector(connector_y, drop=CHILD_DROP)` → `connector_y + drop`
- `resolve_connector_y(*, descender_top, max_label_h, child_y, ...)` → `max(parent_target, child_y - CHILD_DROP)`

## Rules

1. **Child-name drops are relative to the sibling bar, not the parent labels.**
   If the parent-driven target would push the bar too high, `resolve_connector_y`
   lowers it so the bar-to-child drop stays at `CHILD_DROP`.

2. **The parent-to-sibling-bar drop is equally long on both sides of a marriage.**
   When both partners are present, two v-rects are drawn — one per partner descent.

3. **Multi-spouse descenders stagger.** The rightmost group sits highest
   (`child_y - CHILD_DROP`), each group to the left steps down by
   `CHILD_CONNECTOR_STAGGER`. Always run `resolve_connector_y` per group as
   the parent-driven lower bound.

## Tweak the descender length

To shorten the parent-to-sibling-bar drop, lower `DESCENDER_OFFSET` in
`drawio_layout.py`. Try 15–25 px for a noticeably tighter chart; the drop
will equal `offset + max_label_h - (MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1)`
≈ 25 + 90 − 22 = 93 px between parent label bottom and sibling bar (was
~63 px before any reduction).

## Anti-patterns

- Don't recompute `descender_top` or `connector_y` in the generator script.
  Always go through the helpers.
- Don't apply the `MAX_CHILD_NAME_DROP` manual cap in the chart script —
  `resolve_connector_y` already handles the cap.
- Don't draw the child drop line all the way down to the child label — stop
  at `connector_y + 1.0` so the drop reads as one continuous line with the
  bar.
