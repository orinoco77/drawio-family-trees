# Pre-existing layout bug: sibling-bar overlap in `generate_descendants_with_steps.py`

## Symptom

When generating a large descendant chart (roughly 60+ units, 4+ generations
where one sibling's subtree is much wider than another's), the validator
reports many overlapping horizontal connector pairs at the same y:

```
h6 (y=288.0, x=589.0-941.0)  overlaps h7 (y=288.0, x=812.0-1470.0)
h8 (y=374.0, x=146.5-1557.5) overlaps h32 (y=374.0, x=1161.5-1820.5)
h8 (y=374.0, x=146.5-1557.5) overlaps h33 (y=374.0, x=1206.0-3132.6)
...
```

Each `hN` is a horizontal sibling bar (the bar from which each child's
descender drops). Two bars at the same y overlap because one sibling's
subtree grew wider than the gap the algorithm reserved for it.

## Trigger conditions

- A generation has multiple sibling units.
- One sibling has a much wider subtree than its neighbour (e.g. one sibling
  has many descendants of their own, the other has none or few).
- Total descendants > 50, depth ≥ 3.

Confirmed triggers in the Short Main Family Tree GEDCOM:

| Root | Descendants | Depth | Validator |
|---|---|---|---|
| Adam Jonathan Short | 56 | 5 | clean |
| Barlow George Smith | 70 | 4 | ⚠️ overlapping connector pairs |
| Thomas Finigan b.1878 | 70 | 5 | ⚠️ overlapping connector pairs |
| Thomas Finigan b.abt 1820 | 94 | 7 | ⚠️ 34+ overlapping connector pairs |

## Status

This is a **pre-existing regression** in `generate_descendants_with_steps.py`.
Confirmed by:

- Running the script at `git HEAD` (commit `638e143`): same overlaps.
- Running the script at an earlier commit (`d86e377`): same overlaps.
- The previously-saved chart `/home/tv/thomas_finigan_descendants.drawio`
  (94 people, validator-clean) was generated when an even older script
  state handled this case correctly. That commit is no longer in the
  branch and the layout code that worked has been overwritten.

## Affected flagships

When generating any of the following, expect validator warnings:

- Thomas Finigan (b. abt 1820) — `~@I18915667319@` — descendants
- Thomas Finigan (b. 1878) — `~@I18910680676@` — descendants
- Barlow George Smith — `~@I18912139534@` — descendants
- Any other GEDCOM root whose descendant tree has wide-vs-narrow siblings

Charts that pass cleanly today: Edward Grey (`@I19544480083@`),
Adam Jonathan Short (`@I18910540946@`).

## Visual impact

The labels themselves are all distinct and readable. The connector lines
in the affected generation look messy — like two parallel tracks merging
in one row. The rest of the chart is fine. The user can still extract
the genealogical information from the chart, but the rendering is not
"deliverable" by the validator's standard.

## Important: a clean structural linter pass does NOT mean the chart is fine

The structural linter (`validate.py`) reports `0 error(s), 0 warning(s)`
even when the chart has serious visual defects: descenders landing in
the wrong place, families visually merged into a single blob, lines
that look like they come from the wrong name box. The sibling-bar
overlap is the most common of these visual defects, but it is not the
only one.

**When the user reports the chart "looks wrong" or "is a mess" but the
validator passes clean**, the chart is broken. Drop the validator
output and run a visual check with the eye tool. Specific things to
look for when the user complains about a "merged" or "wrong connector"
chart:

- Are the spouse labels in the expected `[S1, Blood, S2]` order (or
  `[Blood, S1, S2, ...]` if the chart explicitly uses descendant
  layout)? If a name that should be on the left is in the middle and
  another that should be in the middle is on the left, the bug is in
  the layout function called *after* the first placement, not in the
  one that ran first.
- For every marriage line, does its descender land in the gap
  between the two name boxes (not next to one of them, and not on top
  of either box)? If a descender is at the same x as a name box's
  left or right edge, the descender is "anchored" to the wrong person.
- Are the two families in a two-spouse root visibly separated, or do
  their children appear in one merged cluster?
- Is the chart's leftmost edge of all content well inside the page
  margin (no content cut off at x=0)?

The `_apply_unit_x` / `place_unit_at_blood_center` inconsistency
documented in `references/descendants-generator-recent-fixes.md`
item 6 was caught by exactly this kind of inspection — the validator
reported clean, but the Thomas-Mary descender landed at x=456.99 next
to Elizabeth's right edge (x=420.49), and Elizabeth's centre (458)
was visually inside the Thomas-Mary marriage gap rather than off to
the left.

## Where to fix

Until the bug is fixed, three options:

1. **Use a different chart type for the same data.** The
   `generate_ancestor_tree_recursive.py` script works fine — it draws the
   bloodline without sibling bars. The line-of-descent script also works
   fine for single-bloodline + siblings.

2. **Drop generations until the chart validates.** Tested: at 2 generations
   the chart is clean; the overlap starts appearing at 3+ generations
   depending on the sibling-tree widths.

3. **Live with the validator warnings.** The validator output for these
   charts is consistent (overlapping sibling bars at one specific
   generation row) and the chart still renders usefully. Note the
   warnings to the user when delivering.

## Where to fix

The fix lives in `generate_descendants_with_steps.py`'s sibling-bar
layout. The script computes each sibling's bar position based on the
sibling's own subtree width, but does not account for the next sibling's
subtree width when reserving horizontal space. Concretely:

- `layout_subtree` returns an `Extent` that includes both the unit's
  width and the children's widest subtree. The child-bar layout uses
  these extents to position each child's bar.
- But when sibling subtrees are placed side-by-side, the gap between
  them must include **half of each neighbouring subtree's width on
  either side** (so the children's descenders don't cross into the
  next sibling's bar).

A robust fix re-runs the layout with a `MIN_SIBLING_GAP` enforced
between neighbouring subtree extents (not just between children's name
boxes). The visit script's `_resolve_overlaps` does this for the
no-overlap recursive layout; the descendant script's multi-spouse
descendant layout does not.

## Don't try to fix the per-bar gap

Don't widen the sibling bar's gap by editing `MIN_SIBLING_GAP` or
`SIBLING_GAP`. The overlap is between the **subtree extents on either
side of a sibling bar**, not between the bar itself and its parent.
Widening the bar's gap doesn't help — it moves the bar but the next
sibling's subtree still reaches into the same x-range.
