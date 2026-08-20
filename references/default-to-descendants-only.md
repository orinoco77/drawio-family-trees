# Default-to-descendants-only decision

## Why the flag was removed

Both `generate_visitation_tree.py` and `generate_descendants_with_steps.py` previously
offered a `--descendants-only` flag. In practice, running either script *without* that
flag produced a mixed (hourglass) chart that included both ancestors and descendants.

For roots with siblings, the mixed path hits the pre-existing sibling-bar overlap bug
documented in `references/descendants-sibling-bar-overlap-bug.md`. The validator then
reports many overlapping connector pairs, which looks like a broken chart but is
actually the expected outcome of combining the mixed-mode connector code with wide-vs-
narrow sibling subtrees.

After repeatedly chasing these warnings as if they were regressions, the decision was
taken to make **descendants-only the default behaviour** and remove the flag entirely.
The supported modes are now:

| Mode | Invocation |
|---|---|
| **Default** — descendants only | omit any mode flag |
| Ancestors only | `--ancestors-only` |

There is no supported mixed/hourglass mode in these two scripts.

## Command patterns that work

### All descendants of a historical root

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_visitation_tree.py \
  --gedcom "/home/tv/Short Main Family Tree.ged" \
  --root-id "@I18915667319@" \
  --all-descendants \
  --output thomas_finigan_1820_descendants.drawio
```

### Descendants with step-children

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_descendants_with_steps.py \
  --gedcom "/home/tv/Short Main Family Tree.ged" \
  --root-id "@I18915667319@" \
  --all-descendants \
  --include-step-children \
  --output thomas_finigan_1820_with_steps.drawio
```

### Ancestors only

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_visitation_tree.py \
  --gedcom "/home/tv/Short Main Family Tree.ged" \
  --root-id "@I18915667319@" \
  --ancestors-only \
  --generations 3 \
  --output thomas_finigan_1820_ancestors.drawio
```

## Distinguishing real breakage from the pre-existing overlap bug

When a large descendant chart validates with a **small number of overlapping horizontal
connector pairs** (`h*` vs `h*`) at the same y-coordinate, and the chart renders as a
wide, readable tree, the overlaps are almost certainly the sibling-bar overlap bug. The
chart is still usable.

Signs of **real breakage** include:

- All labels at roughly the same y-value (lost generational separation).
- Families visually merged into a single cluster.
- Vertical descenders landing next to the wrong name box or on top of a name.
- Lines crossing through labels.
- The validator reports far more overlaps after running *without* `--ancestors-only`
  than it does in the default descendants-only mode.

If in doubt, render the PNG/SVG and look at it. The visual check is authoritative for
relationship correctness; the validator is a geometry linter, not a substitute for
inspection.

## Renderer fallback

`scripts/flatten_export.py` requires a draw.io renderer at `http://localhost:8080`. When
that service is not running, use the installed draw.io CLI directly:

```bash
drawio --export --format svg --output chart.svg chart.drawio
drawio --export --format png --output chart.png chart.drawio
```

The CLI may emit GPU/VAAPI warnings; these are harmless as long as the output file is
created.
