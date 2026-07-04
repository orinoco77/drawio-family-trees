# GEDCOM to Visitation-Style Family Tree

Workflow for turning an Ancestry-style GEDCOM export into a clean, no-box, visitation-book-style Draw.io family tree.

## When to use

- User wants a family tree built from real genealogy data.
- Source is a `.ged` file from Ancestry, Family Tree Maker, Gramps, etc.
- Target style is the no-box, orthogonal-line visitation style used in this project.

## The fast path

Use the generator:

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_visitation_tree.py \
    --gedcom "/path/to/Short Main Family Tree.ged" \
    --root "Brian Stanley Short" \
    --generations 2 \
    --output family_tree.drawio
```

Then render with `scripts/flatten_export.py` and validate with `scripts/verify_family_tree.py` as described in `SKILL.md`.

## Manual workflow (when the generator needs hand-tuning)

### Finding the GEDCOM

GEDCOMs uploaded in past sessions are typically cached under:

```
/home/tv/.hermes/cache/documents/
```

Search with:

```bash
find /home/tv/.hermes/cache/documents -type f -name '*.ged' -o -name '*gedcom*'
```

### Parsing essentials

A minimal GEDCOM parser needs only four record types:

| Record | Key fields | Output |
|---|---|---|
| `INDI` | `NAME`, `GIVN`, `SURN`, `SEX`, `BIRT/DATE`, `FAMC`, `FAMS` | person + birth year + family links |
| `FAM` | `HUSB`, `WIFE`, `CHIL` | spouse/child relationships |

Keep maps keyed by the GEDCOM pointers (`@I123@`, `@F456@`). Birth dates are under a `BIRT` event followed by a `DATE`; track the current level-1 event tag while parsing.

A reusable parser lives at `scripts/parse_gedcom.py`.

## Layout algorithm for an hourglass (ancestors + descendants)

Given a root person (e.g. Brian Stanley Short) and a target of *N* generations:

1. **Collect generations**:
   - Walk up the `FAMC` links to build ancestor generations.
   - Walk down the `FAMS`/`CHIL` links to build descendant generations.
   - Record siblings and spouses at each generation.

2. **Decide what to show**:
   - Show the root's direct ancestors and descendants.
   - Show siblings of the root and of intervening generations if they fit.
   - Show spouses (partners) but do not draw their ancestors unless explicitly asked.

3. **Assign horizontal positions**:
   - For each couple, place the two spouses side by side with a fixed gap (e.g. 40 units).
   - The marriage line bridges the gap; the vertical descender drops from its centre.
   - Centre each child below the midpoint of its parents' marriage line.
   - When multiple children exist, the horizontal child connector spans from the leftmost child centre to the rightmost child centre; the parents' descender meets that connector at its midpoint.
   - Because siblings shift the child-connector midpoint away from the focus person, the focus person will often sit left or right of the geometric centre. That is normal and clean; do not break the orthogonal connector geometry to force the focus person into the exact page centre.

4. **Assign vertical positions**:
   - Use fixed generation row heights (e.g. 130 units).
   - Marriage lines sit near the vertical centre of each text label.
   - Descenders run from the lower marriage line to the horizontal child connector above the next generation.
   - Child-drop lines stop at the **top edge** of the child text label, not in the middle of it.

5. **Connector grammar** (same as the base skill):
   - horizontal marriage line → vertical descender → horizontal child connector → vertical lines to each child.
   - All lines horizontal or vertical; no diagonals, no thick junction bars.
   - Use `shape=rect` (2-unit wide, filled) for vertical segments because `shape=line;direction=south` is ignored by some renderers.

## Example extraction from the Short GEDCOM

Root: Brian Stanley Short (b. 1944)

| Gen | People |
|---|---|
| G1 | William Short & Louisa Roberts; Thomas Finigan & Elizabeth Gardner |
| G2 | Alexander Short & Elsie Finigan |
| G3 | Brian Short & Linda Bolton; Anne Short |
| G4 | Adam Short & Margaret O'Keeffe; Philip Short & Sharon Bayford |
| G5 | Sophie Short; Phoebe Short |

## Anti-patterns specific to GEDCOM trees

- **Dragging in every in-law branch** makes the chart explode. Only show spouses, not their ancestors, unless asked.
- **Including living people without consent** — stick to the data the user supplied.
- **Trusting the renderer with `shape=line;direction=south`** — verticals render horizontally with `tomkludy/drawio-renderer`; use thin rectangles.
- **Drawing a horizontal connector between unrelated couples** — e.g. between the paternal and maternal grandparents of a child. Each couple descends independently to its own child, who then forms a new marriage.

## Non-GEDCOM data

The generator currently reads GEDCOM, but the same `FamilyUnit` layout engine can be driven from any structured source. To use a JSON/YAML list of names and relationships, populate `FamilyUnit` objects directly and call `build_tree` / `generate_drawio`. A generic JSON input adapter is a natural future extension of the generator.