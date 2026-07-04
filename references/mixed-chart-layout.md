# Mixed-chart ancestor block centring

## The symptom

In an hourglass (mixed ancestor + descendant) chart, the ancestor couple immediately above the root generation looks off-centre. For example, with Brian Stanley Short and his sister Anne Elizabeth Short in the root generation, their parents Alexander Short and Elsie Finigan may sit too far to one side, making the top half look lopsided even though the connectors are technically correct.

## Why it happens

The ancestor layout positions each parent unit over the specific child person it descends to:

- William + Louisa are centred over **Alexander**.
- Thomas + Elizabeth are centred over **Elsie**.

Because Alexander and Elsie form a married couple, their respective parent units are 130 units apart (one couple width). The parent couple (Alexander + Elsie) is then placed at the average of the positions those two parent units imply. If the root generation is not symmetric — for instance, one root child is a married couple and the other is single — the parent couple can end up visually off-centre relative to the root generation as a whole.

## The fix

After the bottom-up ancestor layout finishes, shift the entire ancestor block horizontally so the lowest ancestor generation is centred over the midpoint of the root generation.

```python
mixed_mode = include_descendants and include_ancestors and bool(ancestor_gens)
if mixed_mode and ancestor_gens:
    root_blood_centers = [blood_center(u) for u in root_generation_units]
    root_midpoint = (min(root_blood_centers) + max(root_blood_centers)) / 2

    lowest_ancestor_gen = ancestor_gens[-1]
    ancestor_unit_centers = [u.center for u in lowest_ancestor_gen]
    ancestor_midpoint = (min(ancestor_unit_centers) + max(ancestor_unit_centers)) / 2

    delta = root_midpoint - ancestor_midpoint
    if abs(delta) > 0.5:
        for gen in ancestor_gens:
            for unit in gen:
                _shift_unit(unit, delta)
```

Use **unit centres** for the ancestor midpoint (so the couple midpoint is centred), but **blood-person centres** for the root midpoint (so the direct-line children are centred, not their spouses).

## Trade-offs

- The parent couple is now balanced between the root children, which is what users usually expect.
- The individual grandparent couples may no longer have perfectly vertical descenders to Alexander/Elsie; they connect with short horizontal segments instead. In mixed charts this is acceptable and clearer than an off-centre parent block.
- `--ancestors-only` charts should keep straight vertical descenders and do not need this block shift.

## Validation expectation

After the shift, run the same three-mode test as for connector fixes:

```bash
python3 scripts/generate_visitation_tree.py --gedcom tree.ged --root-id "@I..." --generations 2 --output mixed.drawio
python3 scripts/generate_visitation_tree.py --gedcom tree.ged --root-id "@I..." --generations 5 --ancestors-only --output ancestors.drawio
python3 scripts/generate_visitation_tree.py --gedcom tree.ged --root-id "@I..." --generations 2 --descendants-only --output descendants.drawio

python3 scripts/validate.py mixed.drawio
python3 scripts/validate.py ancestors.drawio
python3 scripts/validate.py descendants.drawio
```

All three should report `0 error(s), 0 warning(s)`.
