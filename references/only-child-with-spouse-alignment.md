# Asymmetric child groups are misaligned under the parent

## Symptom

A child group whose units have different widths appears shifted sideways
relative to the parent. The parent-to-child connector no longer drops straight
down into the top centre of the blood child's name; instead it enters from the
side. The most visible case is an only child who has a spouse of their own.

Example: Winifred Finnigan (single parent) → Patricia Finnigan. Patricia is
married to David Gowans, so her unit is `[Patricia, David]`. Before the fix,
Patricia's blood-person centre was ~44 px left of Winifred's centre and the
vertical line ran diagonally into the side of Patricia's label.

## Cause

`layout_subtree` treats each child group's **geometric centre**
`(left + right) / 2` as the point to align with the parent's marriage midpoint.
For a single child with a spouse, the geometric centre is the midpoint of the
whole `[Blood, Spouse]` unit, which sits to the right of the blood person.
Aligning that midpoint with the parent shifts the blood person left.

The same skew happens whenever children in a group have different widths:
children with spouses extend further to the right, pulling the geometric centre
away from the blood-centre midpoint.

## Fix

Use the **blood-centre midpoint** of the children in the group as the alignment
point, not the geometric midpoint.

In `layout_subtree`, when building each `group_extents` entry:

```python
group_blood_centers = [blood_center(c) for c in children]
group_blood_center = (min(group_blood_centers) + max(group_blood_centers)) / 2
group_left = min(e.left for e in child_extents)
group_right = max(e.right for e in child_extents)
group_extents.append((
    spouse_idx,
    Extent(group_left, group_right, group_blood_center, children=child_extents),
))
```

Also return the subtree extent centred on the blood person's centre, so the
alignment is preserved up the tree:

```python
extent_center = blood_center(unit) if unit else (left + right) / 2
return Extent(left, right, extent_center, unit=unit, children=extents_only)
```

This matches the recentering logic already used in `layout_children`:

```python
blood_centers = [blood_center(c) for c in children]
group_center = (min(blood_centers) + max(blood_centers)) / 2
```

## Verification

After the fix, the blood child should have the same x-centre as the parent
above. In the Thomas Finigan chart:

- Winifred Finnigan: centre = 6645.6
- Patricia Finnigan: centre = 6645.6

`verify_family_tree.py` should report no overlapping horizontal child
connectors.

## Scope

Applies to both descendant generators:
- `scripts/generate_descendants_with_steps.py`
- `scripts/generate_visitation_tree.py`
