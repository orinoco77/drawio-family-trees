# Step-Children in GEDCOM Descendant Charts

## The Problem

Standard descendant charts follow bloodlines only. When generating a chart from a root person, the generator follows `FAMS` (family spouse) links to find marriages, then `CHIL` (children) links within those families to find descendants.

This works for blood descendants but misses **step-children** — children from a spouse's previous marriages. In GEDCOM these are separate families where the spouse is linked via `FAMS` but the children live in a different family unit.

Example: Olivia O'Keeffe was previously married to Douglas Clarke-Letton and had children Suzanne and Patricia. When she later marries Adam Short, a standard chart shows Adam + Olivia but not Douglas, Suzanne, or Patricia.

## The Solution: `--include-step-children`

`scripts/generate_descendants_with_steps.py` adds step-children support via the `--include-step-children` flag.

### How It Works

1. Collect blood descendants normally via `FAMS`/`CHIL`.
2. For each blood person's spouse, inspect that spouse's other `FAMS` links.
3. Add each other parent as an **additional spouse** in the same unit, marked with `is_step_parent=True`.
4. Add children from those other marriages as step-children.

Crucially, step-children are stored in the **other parent's** `spouse_children` group, not the blood person's spouse group. This lets marriage lines and child connectors use the correct couple midpoint (current spouse + other parent) rather than the blood-person midpoint.

### Usage

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_descendants_with_steps.py \
    --gedcom family.ged \
    --root-id "@I123@" \
    --generations 5 \
    --include-step-children \
    --output family_with_steps.drawio
```

### Spouse Ordering Convention

Step-parents are appended in the order the spouse's `FAMS` records appear in the GEDCOM. The sort routine that normally reorders spouses by child count **skips** units that contain step-parents, because reordering would break the visual marriage lines.

Resulting layout for a descendant with step-children:

```
[Blood] — [Current Spouse] — [Other Spouse 1] — [Other Spouse 2] ...
```

Example:
```
Adam — Olivia — Douglas — Michael
```

This reads as: Adam married Olivia; Olivia was previously married to Douglas and Michael. The other spouses extend to the right, away from Adam, so there is no visual suggestion that Adam married them.

### Marriage Lines

- A line is always drawn between the blood person and the current spouse (`people[0]` and `people[1]`).
- For each step-parent, a line is drawn between the current spouse (`people[1]`) and that step-parent (`people[i]`), **even if that marriage produced no children who appear in this chart**.
- No line is drawn between the blood person and a step-parent.

Example for `Adam — Olivia — Douglas`:
- Adam–Olivia ✓
- Olivia–Douglas ✓
- Adam–Douglas ✗

### Child Connectors

Children descend from the midpoint of the marriage that produced them:
- Blood children of Adam & Olivia descend from the Adam–Olivia midpoint.
- Suzanne & Patricia (Olivia & Douglas's children) descend from the Olivia–Douglas midpoint.

The layout engine computes marriage midpoints using the actual spouse index, including empty spouse groups, so step-children are centred under the correct couple rather than under the blood person.

### Special Case: Exactly Two Spouses

When a unit contains exactly two spouses total (blood person's spouse + one step-parent), the generator uses the `[S1(left), Blood, S2(right)]` layout for clarity. The same marriage-line and child-connector rules apply.

### Pitfalls fixed during the Short-family session

1. **Step-parent insertion order reversed.** The first implementation inserted each new step-parent immediately after the current spouse (`spouse_idx + 1`). Because later other-marriages were processed after earlier ones, the last step-parent in GEDCOM order ended up closest to the current spouse. Fix: append step-parents at the end of `unit.people` so GEDCOM order is preserved left-to-right.

2. **Child-count sort broke step-parent order.** The normal spouse sort reorders by child count. For step-children this is wrong: it can move a step-parent who has children ahead of the current spouse. Fix: detect `is_step_parent` in the unit and preserve the first spouse; leave step-parents in insertion order.

3. **Layout centred step-children under the blood person.** `layout_subtree` only saw non-empty spouse groups when computing marriage offsets, so a unit like `[Adam, Olivia, Douglas, Michael]` with children only in Douglas's group was centred as if the only marriage were Adam–Olivia. Fix: track the real `spouse_idx` for each child group and compute offsets using the actual marriage midpoints, including empty groups.

4. **Marriage-line drawing used pair order instead of visual order.** The line-drawing code assumed pair `(a, b)` meant `a` was left of `b`. For the `[S1(left), Blood, S2(right)]` layout the pair is `(1, 0)`, producing a line from the wrong edges. Fix: choose left/right based on actual `x` coordinates.

5. **Vision models can misread closely spaced family-tree labels and lines.** When reviewing a rendered chart, an auxiliary vision model may hallucinate marriages between adjacent names (e.g. claiming Douglas is married to Michael when the actual marriage is Olivia–Douglas). Always verify relationship correctness by parsing the generated `.drawio` XML directly when automated vision and human inspection disagree. See the verification recipe below.

6. **Step-parent marriage lines were conditional on having children.** The first implementation only drew a line between the current spouse and a step-parent when `unit.spouse_children[spouse_idx]` was non-empty. This hides valid marriages (e.g. Olivia and Michael Jones) when the marriage produced no children in the chart. Fix: always emit the marriage indicator for a step-parent, independent of children.

7. **Non-descendant multi-spouse marriage lines were chained spouse-to-spouse.** In a unit like `[Current Spouse, Blood Person, Step-Parent A, Step-Parent B]`, the line-drawing code originally produced pairs `(Current, Blood)`, `(Blood, A)`, `(A, B)`, implying A was married to B. Fix: additional spouses are all married to the current spouse, so the pairs must be `(Current, Blood)` and `(Current, A)`, `(Current, B)`.

### Depth: `--all-descendants` does not see step-children

`--all-descendants` auto-detects depth by following blood `FAMS`/`CHIL` links. It does **not** follow a spouse's other marriages, so it will stop before step-children and their descendants.

When using `--include-step-children`, always specify `--generations N` explicitly. If you don't know the depth, estimate high and reduce; or inspect the GEDCOM:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, '/home/tv/.hermes/skills/drawio-family-trees/scripts')
from generate_descendants_with_steps import parse_gedcom

individuals, families = parse_gedcom('family.ged')
# breadth-first walk following both blood children and step-children
PY
```

### GEDCOM Structure Required

1. Person records for blood, spouses, and children.
2. Family records linking spouses via `HUSB`/`WIFE`.
3. Children linked to families via `CHIL`.
4. Spouses linked to multiple families via multiple `FAMS` records.

```
0 @I1@ INDI
1 NAME Adam /Short/
1 FAMS @F1@

0 @I2@ INDI
1 NAME Olivia /O'Keeffe/
1 FAMS @F1@
1 FAMS @F2@

0 @I3@ INDI
1 NAME Douglas /Clarke-Letton/
1 FAMS @F2@

0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@

0 @F2@ FAM
1 HUSB @I3@
1 WIFE @I2@
1 CHIL @I4@
1 CHIL @I5@
```

### Verification

Run the structural checker:

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py family_with_steps.drawio
```

Expected output:
```
All checks passed. The chart is safe to deliver.
```

Because vision models can misread closely spaced family-tree labels and lines, verify relationship correctness by parsing the generated `.drawio` XML directly. Inspect:
- Person `x`/`y` positions.
- Marriage `shape=line` segments (`m*` cells) — check their `x`/`width` spans against the person positions.
- Vertical descenders (`v*` cells) and child drops (`c*` cells) — confirm they originate from the expected marriage midpoint.

Example check for Adam–Olivia–Douglas:

```python
import xml.etree.ElementTree as ET
import re

root = ET.fromstring(open('family_with_steps.drawio').read())
people = {}
for cell in root.iter('mxCell'):
    style = cell.get('style', '')
    value = cell.get('value', '') or ''
    geom = cell.find('mxGeometry')
    if geom is None:
        continue
    if 'text;' in style and 'whiteSpace=wrap' in style:
        clean = re.sub(r'<[^>]+>', '', value).strip()
        people[clean] = float(geom.get('x')) + float(geom.get('width')) / 2

# Adam–Olivia midpoint
m1 = (people['Adam Jonathan Short'] + people["Olivia  O'Keeffe"]) / 2
# Olivia–Douglas midpoint
m2 = (people["Olivia  O'Keeffe"] + people['Douglas Arthur John Clarke-Letton']) / 2
print('Adam–Olivia midpoint:', m1)
print('Olivia–Douglas midpoint:', m2)

for cell in root.iter('mxCell'):
    if cell.get('id', '').startswith('v'):
        geom = cell.find('mxGeometry')
        x = float(geom.get('x')) + 1.0  # 2px-wide rect, centre is x+1
        print(cell.get('id'), 'x=', x)
```

The first vertical descender (`v1`) should be close to `m2` (Olivia–Douglas), not `m1` (Adam–Olivia), because Suzanne and Patricia are step-children of that marriage.

### Limitations

1. `--all-descendants` does not detect step-children depth; specify `--generations` explicitly.
2. Chart width grows with each additional step-parent.
3. Step-parents stay in GEDCOM order; they are not reordered by child count.

### Related

- `scripts/generate_visitation_tree.py` — blood descendants only.
- `scripts/generate_descendants_with_steps.py` — adds `--include-step-children`.
- `scripts/verify_family_tree.py` — structural validation.
- `references/spouse-placement-rules.md` — general spouse placement logic.
