# Single-parent vs couple descender geometry

This reference captures the exact vertical connector tuning used for the Finigan/Short visitation-style descendant charts. The goal is to keep couple descenders long enough for clearance while making single-parent descenders short and clearly detached from the name.

## Desired lengths

| Group type | `descender_top` | Desired length | End `y` relative to parent |
|------------|----------------|----------------|---------------------------|
| Couple     | `y + MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1.0` ≈ `y + 22` | **63 px** | `y + 85` |
| Single parent | `y + TEXT_H + 20.0` = `y + 50` | **45 px** | `y + 95` |

`TEXT_H = 30`, `MARRIAGE_Y_OFFSET = 18`, `MARRIAGE_LINE_GAP = 3`.

## Why per-group desired lengths

A single-parent descender that starts at the text centre or just below the box can look as if it emerges from the name. Starting it **20 px below the box** makes the separation unambiguous. Making it **45 px long** keeps the horizontal child bar at roughly the same level as in previous versions (so child drops and sibling bars do not shift), while the shorter drop reads as a deliberate single-parent connector.

Couple descenders stay at **63 px** (≈ the length that worked for the root couple). Computing the bar position per group means couple-only units are unaffected by the single-parent tuning.

## Unit-level bar position

For each unit with children:

```python
desired_lengths = [45.0 if gi["is_single"] else 63.0 for gi in group_infos]
base_connector_y = max(
    gi["descender_top"] + length
    for gi, length in zip(group_infos, desired_lengths)
)
base_connector_y = max(base_connector_y, unit.y + TEXT_H + 45.0)
```

Then each group is staggered 4 px lower from right to left:

```python
connector_y = base_connector_y + (n_groups - 1 - stagger_idx) * stagger
```

## Side effects

- In **couple-only** units, descenders remain 63 px and end at `y + 85`.
- In **single-only** units, descenders are 45 px and end at `y + 95`.
- In **mixed** units (rare in descendant mode), the bar is raised to the higher required end (`y + 95` if any single group exists), so couple descenders in that unit become ~73 px. This is acceptable because the single-parent bar must be high enough to keep its short drop readable.

## Visual verification

Crop the PNG around a known single parent and check:

1. The vertical line starts visibly below the name box (≈20 px gap).
2. The line is short (≈45 px).
3. The horizontal child bar below sits at the same y as before (≈6 px drop to the child's label).

See `references/visual-verification.md` for the cropping recipe.
