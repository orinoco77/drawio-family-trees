# Paginated ancestor chart: CLI vs debug mismatch

## Symptom

When paginating an ancestor chart for Adam Short (`--ancestors-only --paginate`), the CLI produced:

- **Page 1:** only the focus couple (Adam Short + Olivia O'Keeffe), no parents, no outgoing marker.
- **Page 2:** the ancestor continuation, with an incoming marker.

A small debug script that imported the same functions with the same GEDCOM ID and page size produced:

- **Page 1:** five units (Adam → Brian → Alexander William Walter → William → Alexander Douglas) plus a correct outgoing marker to page 2.
- **Page 2:** six ancestor units.

## Root cause

`paginate_ancestors` compared absolute page extents (`max_y - min_y` vs `page_height - 2 * margin`). The CLI placed the focus person near the bottom of the page:

```python
start_y = args.page_height - args.page_margin - 100
layout_paginated_ancestors(root_unit, args.page_margin, start_y)
```

The debug script placed the focus person at `y = 0`:

```python
layout_paginated_ancestors(root_unit, 0, 0)
```

Because the fit test used absolute coordinates, the large `start_y` offset changed the arithmetic and pushed all ancestor branches onto continuation pages. The paginator itself was correct; it was coordinate-sensitive.

## Fix

Make the paginator operate on relative extents. Subtract the minimum y of the subtree before testing fit:

```python
min_y = min(u.y for u in all_units)
max_y = max(u.y + TEXT_H for u in all_units)
rel_height = max_y - min_y
rel_width = max_x - min_x
```

When deciding whether a branch fits on the current page, compute the combined relative extent of the units already assigned to the page plus the candidate branch. This removes the dependency on `start_y` and makes CLI runs and debug snippets produce identical pagination.

## Secondary fix: positive-height upward connectors

Ancestor connectors logically flow upward (child below, parents above), but draw.io/validator requires vertical line cells to have positive `height` (upper y + positive height = lower y). The renderer must draw:

- Parent-to-bar verticals from the **parent's bottom edge downward** to the horizontal connector bar.
- Child-to-bar verticals from the **bar downward** to the child's top edge.
- Skip horizontal bars of zero width (single-parent units).

## Verification recipe

After fixing, regenerate and validate each page:

```bash
python3 generate_paginated_visitation_tree.py \
    --gedcom "family.ged" \
    --root-id "@I18910540946@" \
    --generations 10 \
    --ancestors-only \
    --paginate \
    --output-prefix adam_ancestors_paginated

for f in adam_ancestors_paginated_page*.drawio; do
    python3 ~/.hermes/skills/drawio-family-trees/scripts/flatten_export.py "$f"
    python3 ~/.hermes/skills/drawio-family-trees/scripts/validate.py "$f"
done
```

Expected result:

- Page 1 contains the focus person plus as many ancestor generations as fit.
- Page 1 has an outgoing continuation marker pointing to page 2.
- Page 2 has an incoming continuation marker from page 1.
- Each page reports `0 error(s)`. The only acceptable warning is the intentional overlap between the marker circle and its number label.
