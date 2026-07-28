# Duplicate Person Markers (Pedigree Collapse)

## Problem

In many real family trees the same individual appears in more than one branch, typically because cousins married or because an ancestor is reached through multiple lines of descent (pedigree collapse). The chart must keep the person in every position so that each branch reads correctly, but the reader also needs a clear signal that those labels refer to the same person.

## Official genealogical practice

Published genealogies handle this in several ways:

- **Merge lines** when space allows: draw the person once and route all connecting lines to that single label.
- **Cross-reference numbers**: show the person in each position with a matching superscript number and a key/legend explaining "¹ = ¹ same person".
- **"See also" notes**: point to another page or chart where the person appears.
- **Ahnentafel numbering**: each ancestor gets a fixed number, so duplicates simply repeat the same number in different positions.

For computer-generated draw.io charts, the cleanest approach is **superscript cross-reference numbers** plus a small legend.

## Implementation in the generator

`generate_visitation_tree.py` now detects duplicates automatically:

1. `collect_duplicate_markers(units)` counts how many times each `indi_id` appears in the rendered chart.
2. Any ID that appears more than once is assigned a unique Unicode superscript marker: `¹`, `²`, `³`, ... (multi-digit markers are built by concatenating superscript digits).
3. `text_cell(..., marker=...)` appends the marker immediately after the person's name, before the birth-year line.
4. If duplicates exist, a small legend is added below the chart. For five or fewer duplicated individuals it lists them by name; otherwise it gives a compact note.

## Example output

```
John of Gaunt¹
(b. 1340)
```

appears wherever John of Gaunt occurs in the chart, and the legend reads:

```
Duplicate persons: John of Gaunt¹; Blanche of Lancaster²
```

## Edge cases

- The marker is added to **every** occurrence, including the first one. There is no canonical "primary" occurrence in a tree, so all duplicates are treated equally.
- The marker is added to the `value` attribute of the text cell; it is not a separate object, so it moves with the label and prints correctly in SVG/PNG exports.
- Very wide charts with many duplicates may need the compact legend note rather than a long list of names.

## Verification

Duplicate markers do not change layout geometry, so the standard validator still applies:

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py chart.drawio
```

Visually confirm that the superscripts are legible at the rendered scale and that the legend does not overlap the chart content.
