# Drawio Family Trees — Layout Rules

Single source of truth for the spacing and descender convention used by every
chart generator in this skill. All generators import these constants from
`scripts/drawio_layout.py`; do not redefine them locally.

## Constants (current values)

| Constant | Value | Meaning |
|---|---|---|
| `TEXT_W` | `75.0` | Width of every person label |
| `DEFAULT_TEXT_H` | `30.0` | Default label height when no live measurement |
| `DEFAULT_TEXT_H_SMALL` | `28.0` | Slightly smaller label height used for the bottom-most generation |
| `MARRIAGE_Y_OFFSET` | `18.0` | Distance from parent label top to marriage line |
| `MARRIAGE_LINE_GAP` | `3.0` | Gap between the two marriage lines for a couple |
| `MARRIAGE_GAP` | `14.0` | Horizontal gap between a couple's two labels |
| `SIBLING_GAP` | `12.0` | Minimum horizontal gap between sibling labels |
| `DEFAULT_GENERATION_HEIGHT` | `105.0` | Legacy constant; newer generators use `min_generation_height(...)` |
| `CHILD_DROP` | `12.0` | Vertical gap from sibling bar to top of child label |
| `DESCENDER_OFFSET` | `-8.0` | Vertical offset from parent label bottom to sibling bar (negative = bar sits above parent label bottom) |
| `INTER_GEN_GAP` | `0.0` | Extra cushion between a generation's bottom and the next's top. Zero by default so the parent-driven sibling-bar position and the child-driven bar cap coincide exactly — any positive value here silently re-introduces a `+INTER_GEN_GAP` px gap above the bar that the user will perceive as "extra space". |

## Core rule

**Child labels are positioned relative to the sibling bar, not the parent labels.**

For each parent group, the sibling bar's y is whichever is lower of:

- `parent_target = descender_top + max_label_h + DESCENDER_OFFSET` (parent-driven)
- `child_cap = child_y - CHILD_DROP` (child-driven cap, ensures bar stays `CHILD_DROP` above children)

This is exposed as `resolve_connector_y(descender_top=..., max_label_h=..., child_y=...)`.

## Generation height formula

Do **not** compute per-generation y as a fixed constant. Use
`min_generation_height(max_label_h)`:

```
min_generation_height(h) = MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1
                         + h + DESCENDER_OFFSET + CHILD_DROP + INTER_GEN_GAP
```

For a 60 px tall label and current constants this is `86.0`. For a 90 px label
this would be `122.0`. Callers should use `CURRENT_GEN_H = min_generation_height(MAX_LABEL_H)`
rather than the legacy `DEFAULT_GENERATION_HEIGHT + (MAX_LABEL_H - DEFAULT_TEXT_H)` formula.

## Descender-top helpers

- `couple_descender_top(root_y)` → `root_y + MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1.0`
- `single_descender_top(root_y, max_label_h)` → `root_y + max_label_h`

## Pitfalls

1. **Don't reintroduce literal descender-length values** (e.g. `45.0`, `63.0`, `desired_lengths`).
   The previous per-script `desired_lengths = [45.0 if is_single else 63.0 for ...]` block
   was replaced by `resolve_connector_y(...)` and must not come back.

2. **Don't redefine `CHILD_DROP` locally.** Older helper functions in some scripts
   still had `CHILD_DROP = 12.0` inside their bodies — strip those on sight.

3. **Don't fall back to the legacy `CURRENT_GEN_H = 165` formula.** It is too large
   for the new offset and reverts the parent descender to 132 px. Always use
   `min_generation_height(MAX_LABEL_H)`.

4. **The patch tool has two modes that look similar but require different
   parameters.** `mode='replace'` accepts `path`, `old_string`, `new_string` only.
   `mode='patch'` accepts a single `patch` parameter containing the V4A format
   string. Mixing them produces errors like "path required" or duplicate outputs.
   When working inside `drawio-family-trees/scripts/*.py`, prefer `mode='replace'`
   for small, well-defined edits and `mode='patch'` for multi-file bulk changes.

5. **The `PATCH` line in the chart XML is a drawio cell, not Python.** When
   inspecting chart files with `grep`/`awk`, look for `<mxCell id="v\d+"` /
   `<mxCell id="h\d+"` / `<mxCell id="c\d+"` — those are the parent descenders,
   sibling bars, and child drops respectively.

6. **Never compute `MAX_LABEL_H` from the whole GEDCOM.** The original bug:
   `global_max = max(estimate_label_height(...) for iid in individuals)`
   picked up long medieval-ancestor names ("Ralph Grey Sheriff of Northumberland,
   Keeper of Roxburgh Castle" → 90 px) and inflated `CURRENT_GEN_H` for a focused
   modern chart. The user's visible symptom is "the descender above the sibling
   bar is way too long even though no one in *this* chart has a long name."
   Always restrict the height calculation to the chart's actual ID set, using a
   BFS bounded by `generations` and the `include_ancestors` / `include_descendants`
   flags. See `references/chart-scoped-max-height.md` for the diagnosis recipe
   and the exact BFS pattern.

## How to tighten or loosen the spacing

| Want to... | Change |
|---|---|
| Shorten parent-to-sibling-bar descender | `DESCENDER_OFFSET` (smaller / more negative) |
| Widen sibling-bar-to-child-label gap | `CHILD_DROP` |
| Add more vertical room between generations | `INTER_GEN_GAP` |
| Move marriage lines up/down | `MARRIAGE_Y_OFFSET` |

Always regenerate *both* the descendant chart and the line-of-descent chart
after a layout change — the latter is the only one that runs cleanly because
it derives `child_y` from the resolved `connector_y`, so any leftover bug
will surface there first.
