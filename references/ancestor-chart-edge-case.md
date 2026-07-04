# Ancestor-only charts: edge case notes

## What makes ancestor charts different from descendant charts

A chart that shows one focus person and **only** their ancestors (no descendants, siblings, aunts, uncles, or cousins) is deceptively different from a descendant chart. The layout must be built **bottom-up**: start with the focus person, then place their parents above them, then each parent's parents above that, and so on. Trying to lay it out top-down means you never know where the lower couples are going to land.

## The failure modes

Early attempts with the visitation generator produced several defects:

1. **No relationship lines.** The descendant-only connector code iterated over `unit.spouse_children`, which was only populated by `build_descendants()`. In ancestors-only mode it stayed empty, so only marriage lines were drawn.
2. **Focus person drifted off-centre.** The overlap-resolution pass that keeps ancestor units from colliding also shifted the root generation, so the focus person no longer sat at the horizontal centre of the chart.
3. **Horizontal child connectors overlapped.** Re-using the descendant connector drawing (horizontal child connectors staggered per spouse) caused many overlapping horizontal segments once the tree widened, because many units in an ancestor generation sit close enough that full-width parent-spanning connectors overlap.
4. **Join bars looked wrong.** A short horizontal bar under each couple solved the overlaps but did not read as a clean "parents → child" descent.

## The current fix

Use the dedicated recursive ancestor generator:

```bash
python3 scripts/generate_ancestor_tree_recursive.py \
    --gedcom "family.ged" \
    --root-id "@I123@" \
    --generations 5 \
    --output ancestors.drawio
```

The generator:

1. Builds a binary tree of couples bottom-up, starting from the focus person.
2. Computes subtree widths recursively: each couple's width is the max of its own natural width and the space needed for the two parent couples above it.
3. Places the focus couple at the bottom centre, then centres each parent couple above its child.
4. Draws a **double marriage line** between each couple and a single **vertical descender** from that marriage line straight down to the child below.

The result is a clean pedigree where every couple joins into one continuous descent line.

## Layout geometry

For a couple (husband, wife):

- Husband and wife are placed side by side with the normal marriage gap.
- The husband's parents are centred above the husband.
- The wife's parents are centred above the wife.
- If the two parent subtrees are wider than the natural couple width, the gap between husband and wife is widened so the parents fit.

This guarantees no text-label overlaps and keeps every child centred under its parents.

## Spouse ancestors

The root couple shows the focus person and their spouse, but **only the focus person's ancestors** are recursed. The spouse is drawn at the bottom because the focus person is married, but their parents are not ancestors of the focus person and are not shown.

## Pedigree collapse

The recursive generator deduplicates by couple key: if the same couple appears again deeper in the tree, the recursion stops and the couple is drawn as a leaf at the deepest occurrence. This keeps the tree finite and avoids exponential blow-up. Duplicate occurrences get unique cell IDs so draw.io never sees duplicate IDs.

## Validation expectations

A correct ancestor-only chart should produce:

```text
0 error(s), 0 warning(s)
```

with `validate.py`.

## Suggested generation depths

| generations | couples | image width | use case |
|-------------|---------|-------------|----------|
| 5 | ~32 | ~8,000 px | book page / shareable image |
| 8 | ~170 | ~43,000 px | large screen / poster |
| 12+ | grows quickly | 50,000+ px | navigable draw.io diagram only |

The width grows with the number of distinct ancestor couples, not the theoretical 2^n maximum, because pedigree collapse and missing lines reduce the real count.

## Export notes for ancestor charts

- The recursive generator sets `background="#ffffff"` on the draw.io page, so the editable diagram and PNG exports use a white page. The SVG export from `convert_file` still returns a transparent background by default; add a white `<rect>` as the first element of the root `<g>` after export.
- Exported PNGs may retain an alpha channel. Flatten them to RGB with a white background if the user sees transparency in their viewer.
- At 8 generations a `scale=2` PNG is still practical (~43,000 px wide). At 12+ generations the renderer may time out at `scale=2`; use `scale=1` for the PNG and rely on the SVG / `.drawio` source for zoom.
