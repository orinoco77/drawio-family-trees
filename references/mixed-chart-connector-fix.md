# Mixed (hourglass) ancestor/descendant charts

## The symptom

In a mixed chart (ancestors above the focus person, descendants below), the ancestor half looks wrong:

- Two unrelated parent couples appear joined by a long horizontal line.
- Vertical lines drop to the wrong person in a child unit, or miss the child unit entirely.
- The validator reports overlaps between `c*` child drops, or between lines and marriage lines.
- Dangling vertical lines appear on the right that do not connect to any rendered person.

Example from the Short tree:

```text
William Short + Louisa Elizabeth Roberts
            │
            └── Alexander William Walter Short + Elsie Gardner Finigan
                         │
            Thomas Finigan + Elizabeth Ann Gardner
```

## Root causes

### 1. Descendant-style connectors do not work for ancestor links

A married child unit (e.g. Alexander + Elsie) is linked from **two** parent units above:

- William/Louisa connect to **Alexander**.
- Thomas/Elizabeth connect to **Elsie**.

The descendant-style connector draws a horizontal bar from the parent couple's marriage centre to the child unit's blood-person centre. When two parent couples do this to the same child unit, their horizontal bars overlap and the drops both land at the blood person's centre, producing the "joined unrelated couples" look and duplicate drops.

### 2. Root-generation siblings are linked but not rendered

The ancestor layout links parents to every child person in the current generation, including root-generation siblings of the focus person. If those sibling units are not added to the flat `units` list, their text labels are never emitted, but their connector lines are — resulting in dangling vertical lines.

### 3. Stored child centres must be shifted with the diagram

When the diagram is auto-fitted to the page, every `person.x` is shifted by `dx`. `FamilyUnit.child_centers` stores the child's x-coordinate at layout time, so it must be shifted by the same `dx` or the connector will point to the wrong place.

## The fix

Use **per-child-person** connectors for ancestor links in mixed charts:

1. Record which person in each child unit belongs to each parent unit:
   ```python
   parent_unit.child_centers[id(child_unit)] = person.x + TEXT_W / 2
   ```
2. Shift those stored centres when the diagram is shifted to fit the page:
   ```python
   for unit in units:
       unit.center += dx
       for person in unit.people:
           person.x += dx
       for key in unit.child_centers:
           unit.child_centers[key] += dx
   ```
3. Draw ancestor links separately from descendant links:
   - For each parent/child-person pair, draw a vertical descender from the parent couple's marriage centre down to the connector level.
   - Draw a horizontal line from the parent marriage centre to the specific child person's centre.
   - Draw a vertical drop from that child centre down to the child.
4. Include root-generation siblings in the rendered units list so their labels and connectors both appear.

## Validation expectation

A correct mixed chart should produce:

```text
0 error(s), 0 warning(s)
```

Even after the connector geometry is fixed, the ancestor block may still look off-centre if the root generation is asymmetric (e.g. a married focus person plus a single sibling). Apply the separate ancestor-block centring step described in `references/mixed-chart-layout.md`.

Test all three modes after any change to the connector code:

```bash
python3 scripts/generate_visitation_tree.py --gedcom tree.ged --root-id "@I..." --generations 2 --output mixed.drawio
python3 scripts/generate_visitation_tree.py --gedcom tree.ged --root-id "@I..." --generations 5 --ancestors-only --output ancestors.drawio
python3 scripts/generate_visitation_tree.py --gedcom tree.ged --root-id "@I..." --generations 2 --descendants-only --output descendants.drawio

python3 scripts/validate.py mixed.drawio
python3 scripts/validate.py ancestors.drawio
python3 scripts/validate.py descendants.drawio
```

## When this does not apply

- **Ancestor-only charts** use `generate_ancestor_tree_recursive.py`, which draws a single vertical descender from each couple to the child below and does not need per-child-person connectors.
- **Descendant-only charts** do not have the in-law ambiguity because each child unit is claimed by only one parent unit.
