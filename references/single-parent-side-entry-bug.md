# Single-parent child groups: side-entry bug

## Symptom

In a descendant chart, a child whose parent has no recorded spouse gets a connector
that enters the child label from the **side** instead of dropping straight down from
the parent. The horizontal child connector is visibly long and off-centre, and the
parent looks as if it belongs to a different family.

Example from the Short/Finigan tree: Winston James Buck and Lee Scott Fitzgerald
(children of single-parent families) had their parent centres 89–134 px to the right
of the child centres, so the line ran horizontally into the side of the name.

## Root cause

The recursive layout in `layout_subtree` treats every non-empty child group as if it
belongs to a marriage and applies a horizontal offset from the blood person's centre.
For a child group stored at `spouse_idx == 0` (the "no spouse" / single-parent slot),
the correct offset is **zero**: the child's centre should align with the blood person's
centre. The old code applied couple-style offsets (e.g. `-step/2` or `-1.5*step`) to
single-parent groups, shoving the child sideways.

## Where it lives

- `scripts/generate_descendants_with_steps.py` — `layout_subtree` computes offsets
  with spouse_idx-aware branching but did not special-case `spouse_idx == 0`.
- `scripts/generate_visitation_tree.py` — `layout_subtree` lost spouse_idx information
  while building `group_extents`, then called `_marriage_offsets(len(group_extents))`,
  which treated a single-parent group as if it were the first marriage.

## Fix

In both scripts, explicitly return offset `0.0` when `spouse_idx == 0`:

```python
def _group_offset(spouse_idx: int) -> float:
    if spouse_idx == 0:
        return 0.0
    # ... couple / multi-spouse offsets ...
```

For `generate_visitation_tree.py` this required refactoring `layout_subtree` to keep
`(spouse_idx, extent)` tuples instead of discarding the index.

## Verification

After the fix:

- The validator's horizontal-connector-overlap check passes (no `h*` vs `h*` overlaps).
- A single parent's vertical descender lands directly above the child centre.
- Visual inspection shows the line entering the top of the child label, not the side.

## Related

- `references/single-vs-couple-descenders.md` — vertical descender length for single parents
- `references/connector-geometry.md` — general connector conventions
