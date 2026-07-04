# draw.io Family Trees

Clean, minimal family tree / pedigree diagrams in draw.io, generated from GEDCOM files or built by hand.

This is a [Hermes Agent](https://hermes-agent.nousresearch.com/) skill. It can also be used standalone from the command line.

## What it produces

- No boxes around names — plain top-aligned text labels.
- Orthogonal connectors only: horizontal marriage lines, vertical descenders, horizontal child connectors, vertical child drops.
- Double-line marriage connectors.
- Blood children centred under their parents; spouses extend to the side.
- Recursive, overlap-free layout for large descendant trees.

## Install as a Hermes skill

```bash
# Clone into your Hermes skills directory
git clone https://github.com/YOUR_USERNAME/drawio-family-trees.git \
  ~/.hermes/skills/drawio-family-trees
```

Restart or refresh Hermes and the `drawio-family-trees` skill will be available.

## Standalone usage

All scripts are self-contained Python 3 and live in `scripts/`.

### Generate a descendant-only tree from a GEDCOM

```bash
python3 scripts/generate_visitation_tree.py \
    --gedcom "family.ged" \
    --root-id "@I123@" \
    --all-descendants \
    --descendants-only \
    --title "Descendants of William Short" \
    --font-family "Times New Roman" \
    --output descendants.drawio
```

- `--title` overrides the default title.
- `--font-family` sets the font for labels and title (default `Helvetica`).

### Render to PNG/SVG

```bash
python3 scripts/flatten_export.py descendants.drawio
```

This requires a draw.io renderer at `http://localhost:8080`. The easiest way is:

```bash
docker run -d --name drawio-renderer -p 8080:5000 --shm-size=1g tomkludy/drawio-renderer:latest
```

### Validate before delivery

```bash
python3 scripts/verify_family_tree.py descendants.drawio
```

A deliverable chart must report:

```
All checks passed. The chart is safe to deliver.
```

The verifier runs:

1. The structural linter (`scripts/validate.py`) — must be `0 error(s), 0 warning(s)`.
2. Generational separation — one distinct y-value per generation.
3. Connector overlap detection — no horizontal child connectors from different families sharing the same y-level.

## Scripts

| Script | Purpose |
|---|---|
| `generate_visitation_tree.py` | GEDCOM → draw.io (descendants and hourglass trees). |
| `generate_ancestor_tree_recursive.py` | GEDCOM → draw.io ancestor-only tree. |
| `generate_vertical_pedigree.py` | GEDCOM → direct-line vertical pedigree. |
| `flatten_export.py` | Render `.drawio` to PNG/SVG via localhost renderer. |
| `validate.py` | Structural linter for `.drawio` files. |
| `verify_family_tree.py` | Pre-delivery checker (linter + geometry checks). |
| `parse_gedcom.py` | Minimal reusable GEDCOM parser. |

## Documentation

See `SKILL.md` and the `references/` directory for detailed conventions, pitfall notes, and worked examples.

## License

MIT.
