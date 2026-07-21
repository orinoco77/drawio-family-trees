# Paginated family trees for book layout

For very large descendant (or ancestor) branches, a single diagram can become too wide to print legibly even at scale=1. One book-friendly solution is to **split the tree across several page-sized diagrams** and join them with numbered off-page continuation markers.

## When to use this

- A descendant branch has more people than fit comfortably on one A4/Letter spread.
- You want to keep the existing visitation-style geometry (thin orthogonal lines, top-aligned labels, double marriage lines) rather than redesign the visual language.
- Readers can follow a numbered marker from one page to the next.

## Convention for continuation markers

A marker is a small circle containing a reference number. It replaces the subtree that would not fit on the current page.

On the parent page the marker sits **in place of the person's name label**:

```
Thomas Finigan (b. abt 1820) ─── Mary
             │
    ───────────────────
    │          │          │
 Ellen    James     Catherine
            (2)         John
```

On the continuation page the same number appears at the top and leads into the continued person, whose name is shown in full:

```
        ◯
        2
        │
  James Finigan (b. 1846) ─── Margaret
              │
      ────────c──────
      │        │        │
   Thomas     Mary      Ann
```

**Why hide the name on the parent page?** Showing the full name on both pages makes it look like there are two different people. The marker alone signals "this person is continued on page N"; the name appears only once, on the continuation page.

Rules that keep the system readable:

1. **Marker replaces the name on the parent page.** Do not repeat the person's name above the marker.
2. **Show the name on the continuation page.** The incoming marker leads directly into the labelled person.
3. **One marker per broken branch.** If a person has multiple spouses with many descendants, you can break the whole person out to a new page with one marker.
4. **Bi-directional markers.** Page *n* shows a "(2)" marker leading forward; page *n+1* shows "2" at the top leading backward/into the new root.
5. **Keep markers visually distinct.** Use a circle or rounded rectangle with the same stroke weight as the family connectors.

## Implementation approach

### Branch-based, page-filling pagination (preferred)

A clean pagination is **branch-based** rather than raw geometric tiling, and each page should be **filled as much as possible** before using continuation markers. A page that contains only the root couple and a row of outgoing markers is wasteful and uninformative.

The prototype at `/home/tv/paginated_prototype/generate_paginated_visitation_tree.py` implements this for both descendants and ancestors. It uses **dedicated paginated layouts** rather than post-processing the unbounded visitation layout, because the standard visitation layout centres children under the marriage midpoint and can place descendants to the left of the root blood person. That makes root-on-page-1 pagination almost impossible without a major relayout.

#### Descendant pagination

1. Build the descendant tree as usual.
2. Lay out with a **left-to-right recursive layout**: root at the left margin, spouses extend to the right, children placed in the next generation left-to-right by spouse group.
3. Recursively paginate by branch: try to fit the whole subtree on one page; if it does not fit, keep the root on the current page and add child branches left-to-right until the page is full; continue each overflow branch on its own page sequence.
4. Draw outgoing markers on the parent page for each child branch that continues elsewhere; draw incoming markers at the top of each continuation page.

Usage example:

```bash
python3 /home/tv/paginated_prototype/generate_paginated_visitation_tree.py \
    --gedcom "family.ged" \
    --root-id "@I18912281927@" \
    --all-descendants \
    --descendants-only \
    --paginate \
    --output-prefix thomas_maxwell_greig_paginated
```

This emits `*_page001.drawio`, `*_page002.drawio`, etc. Each page is an A4-sized slice; continuation markers link split branches.

#### Ancestor pagination

1. Build an ancestor tree linked via a `parents` field on each `FamilyUnit`.
2. Lay out with a **bottom-up recursive layout**: the focus person sits near the bottom of the page, parents are placed above at `y - GENERATION_HEIGHT`, laid out left-to-right.
3. Recursively paginate by branch: fit as many ancestor generations as possible on the current page; when a parent's subtree no longer fits vertically/horizontally, mark it for continuation and continue it on a new page.
4. Draw outgoing markers **above** a unit whose ancestors continue elsewhere; draw incoming markers **below** a unit that continues from a previous page.

**Pitfall — ancestor pagination is sensitive to absolute `y` coordinates.** The fit test in `paginate_ancestors` compares absolute page extents (`max_y - min_y` vs `page_height - 2 * margin`). If the layout places the root at `start_y = page_height - margin - 100` but the paginator was written assuming the root near `y = 0`, the arithmetic still works, but any debug script that uses a different `start_y` will produce different pagination. If you see page 1 unexpectedly contain only the root couple while the CLI produces a fuller page, check whether a debug snippet used `layout_paginated_ancestors(root, 0, 0)` while `main()` uses `layout_paginated_ancestors(root, margin, page_height - margin - 100)`.

**Fix — make the paginator operate on relative extents.** Before testing fit, subtract the minimum y of the subtree from all y values:

```python
min_y = min(u.y for u in all_units)
max_y = max(u.y + TEXT_H for u in all_units)
rel_height = max_y - min_y
rel_width = max_x - min_x
```

When adding a branch to the current page, compute the combined relative extent of the units already on the page plus the candidate branch. This removes the dependency on `start_y` and makes CLI and debug-script runs identical. Apply the same principle to descendant pagination if it ever shows similar start-coordinate sensitivity.

**Pitfall — upward vertical connectors must be drawn with positive height.** draw.io/validator treats a vertical line cell with negative `height` as invalid. For ancestor connectors, draw the child-to-parent verticals from the **parent's bottom edge downward** to the connector bar, and the child-to-bar vertical from the **bar downward** to the child's top edge. In other words, always use `y` as the upper endpoint and `height = lower_y - upper_y`, even when the geometry logically flows upward. Horizontal bars with zero width (single parent) should be skipped.

Usage example:

```bash
python3 /home/tv/paginated_prototype/generate_paginated_visitation_tree.py \
    --gedcom "family.ged" \
    --root "Adam Short" \
    --generations 10 \
    --ancestors-only \
    --paginate \
    --output-prefix adam_ancestors_paginated
```

#### Recursive pagination algorithm (page-filling, branch-based)

The core routine, `paginate_branch(unit, page_width, margin)`, works like this:

1. Compute the unit's subtree extent after layout.
2. If the whole subtree fits on one page, return a single page containing it.
3. Otherwise, start a new page with the unit alone.
4. Walk the unit's child branches left-to-right. For each branch:
   - Compute the branch's subtree extent.
   - If the branch fits on the current page, add all of its units and merge its outgoing markers.
   - If it does not fit, record an outgoing marker for the branch and recursively paginate the branch. The first page of the recursive result becomes the start of the branch's continuation sequence.
5. After all branches are processed, resolve outgoing markers to actual page numbers and add incoming markers to the first page of each continuation sequence.

The same logic applies to ancestors via `paginate_ancestors(unit, ...)`, using `unit.parents` instead of `unit.spouse_children`.

This greedy, branch-first approach keeps sibling groups intact and avoids the empty-root-page problem that occurs when every child immediately gets its own page.

#### Marker drawing rules

| Mode | Incoming marker | Outgoing marker | Internal connectors |
|------|-----------------|-----------------|---------------------|
| Descendants | Top of a continued child, number = source page | Below a parent whose child branch continues, number = target page | Parent → child, downward |
| Ancestors | Bottom of a continued unit, number = source page | Above a unit whose parents continue, number = target page | Child → parent, upward |

The renderer must switch connector functions based on mode; do not reuse descendant connectors for ancestor charts or lines will point the wrong way.

#### Rendering and validating each page

Render each page and run the pre-delivery checker:

```bash
for f in *_page*.drawio; do
    python3 ~/.hermes/skills/drawio-family-trees/scripts/flatten_export.py "$f"
    python3 ~/.hermes/skills/drawio-family-trees/scripts/validate.py "$f"
done
```

Each page should report `0 error(s)`. A single warning about the continuation marker's circle and number overlapping is intentional (the number is drawn on top of the circle) and can be ignored. Any other overlap or non-positive-size warning indicates a connector geometry bug.

### Minimal hand-built prototype

A tiny standalone prototype (two-page Thomas Finigan → James Finigan example) is available at `scripts/paginated_tree_prototype.py`. It is useful for testing marker styling without the full GEDCOM pipeline.

## Pitfalls

- **Do not put only the root couple on page 1.** Readers want page 1 to contain as much of the tree as possible. Only break out a child branch when it no longer fits.
- **Do not try to paginate by slicing the standard visitation layout.** The standard layout can place the root in the middle of its descendants, making root-on-page-1 impossible without relayout. Use a dedicated paginated layout instead.
- **This is not automatic A4 tiling.** The split is still branch-oriented, because branch cuts are meaningful to a reader.
- **Remember to set `unit.y` in dedicated layouts.** A custom layout that positions `person.x`/`person.y` but forgets to update `unit.y` will cause all labels to collapse onto one horizontal line and produce hundreds of overlap warnings.
- **Very wide single generations** (e.g. 15+ siblings) may still not fit on one page. In that case split by sibling sub-branches instead.
- **Always run `validate.py` on each emitted page before delivery.**
