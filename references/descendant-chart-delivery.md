# Delivering Wide All-Descendant Charts

## When this applies

You have used `generate_visitation_tree.py` with `--all-descendants` or `--descendants-only` and produced a chart that spans many generations. These charts grow wide quickly because every branch must remain contiguous and every name must remain readable.

## What to expect

- A 7-generation descendant tree can easily be **8,000–15,000 px wide** at the default scale.
- At `scale=2`, the PNG may be 10,000–30,000 px wide.
- Telegram and similar clients downscale wide images to fit the chat bubble, so individual names become unreadable in the inline preview.

## Delivery rule

Always deliver **all three** formats and explain which one to use:

| File | Purpose |
|------|---------|
| `.drawio` | Editable source; open in diagrams.net to pan, zoom, and edit. |
| `.svg` | Zoomable vector image; good for reading names in a browser or image viewer. |
| `.png` | Quick preview/thumbnail; may be too wide to read inline. |

Suggested wording for the user:

> The PNG is very wide, so it may look small in chat. Use the `.drawio` or `.svg` file to zoom in and read every name.

## Verifying the chart matches the GEDCOM

Before delivering, quickly check that the expected people are present and the deepest generation looks right. Use the skill's own parser:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, '/home/tv/.hermes/skills/drawio-family-trees/scripts')
from parse_gedcom import parse_gedcom, get_name

individuals, families = parse_gedcom('family.ged')
root_id = '@I19544480083@'

visited = set()
def collect(person_id, generation=0):
    if person_id in visited:
        return
    visited.add(person_id)
    ind = individuals.get(person_id, {})
    print(f"G{generation}: {get_name(person_id, individuals)}")
    for fam_id in ind.get('fams', []):
        for child_id in families.get(fam_id, {}).get('chil', []):
            collect(child_id, generation + 1)

collect(root_id)
print(f"\nTotal unique descendants (including root): {len(visited)}")
PY
```

## Validator warnings

For multi-spouse descendant charts, `validate.py` may report many "overlaps" between `h*`, `v*`, and `c*` line segments. These are normally intentional junctions where:

- a vertical descender meets a horizontal child connector,
- multiple marriage lines share the blood-person endpoint, or
- child-drop lines meet sibling bars.

If there are **0 errors** and no warnings involve person-label cells (`p*`), the chart is structurally sound. If you see label overlaps, the layout constants need tuning or the tree is too wide for the chosen page size.

## If the PNG is still unreadable

1. Open the `.drawio` file in diagrams.net and zoom in.
2. Export just the visible portion as a new PNG at higher scale.
3. Consider splitting the tree by major branch if it must fit a printed page.
