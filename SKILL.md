---
name: drawio-family-trees
description: Create clean, minimal family tree / pedigree diagrams in draw.io from GEDCOM or hand-rolled data. Optimised for clarity and avoiding the common visual artefacts that make hand-built trees look wrong.
version: 1.22.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [drawio, family-tree, genealogy, pedigree, diagram, gedcom]
    category: drawio-family-trees
    related_skills: [drawio-skill]
---

# Family Trees in Draw.io

## When to use

Use for genealogy, pedigree charts, generational relationship diagrams, or any parent-child-sibling visualisation where the user wants a clean, conventional tree layout. Supports both hand-built diagrams and GEDCOM-driven generation.

## Locked-in conventions for this chart style

These conventions produced the final Short-family chart and should be treated as the default for future visitation-style trees unless the user explicitly asks to change them:

1. **Blood child is centred under the parent.** When a child is married, place the blood-relative person directly under the parent's marriage line; the spouse extends to the right. Do not centre the couple midpoint under the parent.
2. **Connectors touch blood children only.** The horizontal child connector spans the blood-child centres. Vertical child-drop lines terminate at the blood child's top edge, never at a marriage separator.
3. **Descenders come from the parent's marriage centre.** The vertical line from a parent couple drops from the midpoint of their double marriage line, meets the child connector, then branches to each blood child.
4. **Marriage lines sit at the visual centre/baseline of the name labels.** The double marriage line is drawn behind the labels (`fillColor=#ffffff`) so the names remain perfectly legible. The line sits roughly two-thirds down the text box, keeping spouses visually aligned; it does not dangle below the names.
5. **Multiple spouses.** The blood person stays in the centre; spouses alternate right/left, ordered by child-count descending (largest child group on the outside). Each marriage's children form a contiguous block descending from that marriage line. Children are ascribed to the correct spouse using the GEDCOM `FAMC` link. The horizontal **child connectors** for different spouses are staggered vertically (**4 px per spouse**), with the **rightmost group highest** so descenders never cross. The connector always extends from the marriage line to the outermost child, so children sitting far to the side remain visibly connected to the right parent. The marriage double-lines themselves remain at the same height.
6. **Recursive, overlap-free layout for large descendant trees.** For descendant-only charts the generator uses a bottom-up subtree layout: each subtree is sized to its contents, parent units are centred over their children, and sibling subtrees are separated by a minimum gap. This guarantees no text-label overlaps; the chart grows as wide as necessary.
7. **Ancestor charts are built bottom-up.** Use the dedicated recursive ancestor generator. Start with the focus person, place their parents above them, then each parent's parents, and so on. Each couple gets a double marriage line and a single vertical descender straight down to the child below. The child is centred under the couple.
8. **Keep the focus person centred in ancestor charts.** The root generation is anchored at the page centre and is not shifted by ancestor overlap resolution.
9. **Deduplicate lines for pedigree collapse.** The same ancestor may appear above the same child through multiple lines of descent. Emit only one line segment for identical parent→child geometry, and give duplicate person occurrences unique cell IDs.
10. **Compact proportions.** Default constants:
    - `TEXT_W = 75`
    - `TEXT_H = 30`, `TEXT_H_SMALL = 28`
    - `MARRIAGE_GAP = 14`
    - `MIN_SIBLING_GAP = 12`
    - `GENERATION_HEIGHT = 105`
    - `MARRIAGE_Y_OFFSET = 18`, `MARRIAGE_LINE_GAP = 3`
    - Name labels are **top-aligned** (`verticalAlign=top`) so every name in a generation begins at the same y; long names then extend downward and do not ride up into connector lines above.
    - Single-parent vertical descenders start **20 px below the bottom of the name box** (`descender_top = y + TEXT_H + 20.0`), not at the text centre, so the line is clearly below the name.
    - Desired descender lengths are computed **per group**: **45 px for single-parent groups** and **63 px for couple groups**. The horizontal child-bar position for a unit is the highest required end of any of its groups, staggered 4 px lower for each group to the left.
    - The vertical descender from a parent (or parent couple) ends **1 px below the horizontal child-bar** (`connector_y + 1.0`). This overlap is hidden by the sibling bar when present; for an only child with no sibling bar drawn, it closes the 1 px gap between the descender and the child-drop line that would otherwise appear just above the name.
    - Vertical child drops start **just below the sibling bar** (`connector_y + 1.0`) and stop **3 px above the child's label** (`child.y - 4.0`). The small gap is not visible in normal rendering and prevents the line from touching the text.
11. **Auto-fitted page.** The draw.io page is sized to the content bounding box plus a small margin; no surrounding whitespace.
12. **Intermarried ancestors.** When two people from different families marry (e.g. Alexander Short & Elsie Finigan), each set of parents is centred over its own child. The marriage gap between the intermarried couple widens as needed so the parent units do not overlap.
13. **No boxes around names.** Plain top-aligned text labels (`text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=top;...`).
14. **Orthogonal lines only.** Horizontal/vertical `shape=line` for marriage and child connectors; thin `shape=rect` for vertical descenders and child drops to survive PNG export.
15. **Double marriage lines.** Two parallel horizontal lines between spouses. Accept that PNG export may collapse them; the editable draw.io source and SVG preserve them.

## Quick path from GEDCOM to rendered tree

If the user wants a tree from a GEDCOM file:

1. Find the cached `.ged` file under `~/.hermes/cache/documents/`.
2. Run the generator:
   ```bash
   python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_visitation_tree.py \
       --gedcom /path/to/tree.ged \
       --root "Brian Stanley Short" \
       --generations 2 \
       --output family_tree.drawio
   ```
3. Render with the local draw.io renderer. The recommended way is the bundled helper script, which handles white backgrounds and PNG alpha flattening and falls back from `scale=2` to `scale=1` if the renderer times out:
   ```bash
   python3 ~/.hermes/skills/drawio-family-trees/scripts/flatten_export.py family_tree.drawio
   ```
   Or manually:
   ```bash
   docker run -d --name drawio-renderer -p 8080:5000 --shm-size=1g tomkludy/drawio-renderer:latest
   sleep 5
   curl -s -d @family_tree.drawio -H "Accept: image/png" \
       "http://localhost:8080/convert_file?border=10&scale=2" -o family_tree.png
   curl -s -d @family_tree.drawio -H "Accept: image/svg+xml; charset=utf-8" \
       "http://localhost:8080/convert_file?border=10&scale=2" -o family_tree.svg
   docker stop drawio-renderer && docker rm drawio-renderer
   ```
   If you use the manual path, remember to inject a white background into the SVG and flatten the PNG alpha channel (the helper script does both).
4. Validate with the pre-delivery checker (runs the linter, checks generational separation, and detects conjoined-family connector overlaps):
   ```bash
   python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py family_tree.drawio
   ```
   Do not treat a non-zero warning count as acceptable. A deliverable descendant chart must report:
   ```
   All checks passed. The chart is safe to deliver.
   ```
5. If the checker reports issues, dig deeper:
   - Run `validate.py` directly for the raw linter output.
   - Verify generational separation: a correct chart has one distinct y-value per generation, not all names clustered on one or two horizontal lines.
   - Verify connector separation: horizontal child connectors from different parent units must not overlap horizontally at the same y-level.
   See `references/visual-verification.md` and `references/descendant-layout-y-position-bug.md` for the recipes.
6. Visually inspect the rendered PNG/SVG. Automated checks do not catch crowding, lopsided spacing, or lines that look wrong to a human eye.
7. Show the PNG/SVG and the editable `.drawio` source.

### Titles and fonts

All three generators accept `--title` and `--font-family`:

```bash
python3 scripts/generate_visitation_tree.py \
    --gedcom family.ged \
    --root-id "@I123@" \
    --all-descendants \
    --descendants-only \
    --title "Descendants of William Short" \
    --font-family "Times New Roman" \
    --output family_tree.drawio
```

- `--title` overrides the default title derived from the root person's name.
- `--font-family` sets the draw.io `fontFamily` for every person label and the title. The default is `Helvetica`. Use a font name draw.io recognises (e.g. `Arial`, `Times New Roman`, `Georgia`, `Courier New`).

The generator produces a **no-box, visitation-style** tree with orthogonal connectors and double-line marriage connectors.

## Core geometry (orthogonal, `shape=line`)

Use `shape=line` with explicit directions for precise, repeatable geometry. Do **not** use draw.io edges for family connectors — edges route automatically and can introduce diagonals or breaks.

The connector grammar is:

1. **Marriage line** — horizontal `shape=line;direction=east` between spouses.
2. **Vertical descender** — one `shape=line;direction=south` from the centre of the marriage line down to the child-junction level.
3. **Horizontal child connector** — one `shape=line;direction=east` spanning above the children.
4. **Vertical child lines** — `shape=line;direction=south` from the child connector down to each child box.

```
Arthur ─────── Dorothy
            │
            │
    ─────────────
    │              │
Robert        Margaret
```

All line segments must be strictly horizontal or vertical. No diagonals, no curved corners, no thick junction bars.

## Style rules

- **Person labels**: plain text cells (`text;html=1;strokeColor=none;fillColor=#ffffff;align=center;verticalAlign=top;...`) with white fill so connector lines drawn behind them are hidden. Name and birth year on separate lines. No boxes.
- **Explicit white background behind every label.** draw.io's `fillColor` on an html text cell is not always enough to hide connector lines in raster export. Emit a separate white `shape=rect` (`fillColor=#ffffff;strokeColor=none`) with the same geometry as the label, drawn **before** the connector lines, and place the text cell on top. Use IDs `{cell_id}_bg` for the rect and `{cell_id}` for the text. The structural linter will report an overlap; update the linter to ignore intentional `{id}_bg` / `{id}` pairs.
- **Line weight**: consistent `strokeWidth=1.5` everywhere.
- **No arrowheads** on family relationships.
- **No thick junction bars**: the horizontal child connector should be a thin line, not a filled rectangle.
- **Continuous descender**: align the vertical descender so it passes straight through the horizontal child connector.

## Recommended XML

```xml
<!-- Visitation-style label: white background rect drawn first, then text on top -->
<mxCell id="p1_bg" value="" style="shape=rect;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=none;" vertex="1" parent="1">
  <mxGeometry x="330" y="40" width="75" height="30" as="geometry" />
</mxCell>
<mxCell id="p1" value="Arthur Bennett&#xa;(b. 1945)" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=center;verticalAlign=top;whiteSpace=wrap;rounded=0;fontSize=11;fontColor=#333333;" vertex="1" parent="1">
  <mxGeometry x="330" y="40" width="75" height="30" as="geometry" />
</mxCell>

<!-- Marriage line -->
<mxCell id="m1" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
  <mxGeometry x="405" y="60" width="40" height="1" as="geometry" />
</mxCell>

<!-- Vertical descender (use shape=rect for reliable PNG/SVG export) -->
<mxCell id="v1" value="" style="shape=rect;whiteSpace=wrap;html=1;fillColor=#333333;strokeColor=none;" vertex="1" parent="1">
  <mxGeometry x="424" y="61" width="2" height="45" as="geometry" />
</mxCell>

<!-- Horizontal child connector -->
<mxCell id="h1" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
  <mxGeometry x="200" y="106" width="540" height="1" as="geometry" />
</mxCell>

<!-- Vertical child line -->
<mxCell id="c1" value="" style="shape=rect;whiteSpace=wrap;html=1;fillColor=#333333;strokeColor=none;" vertex="1" parent="1">
  <mxGeometry x="199" y="106" width="2" height="70" as="geometry" />
</mxCell>
```

## Anti-patterns to avoid

1. **Edges instead of `shape=line`.** Edges auto-route and can produce diagonals or off-centre junctions.
2. **Thick filled junction bars.** The child connector should be a thin line, not a dark grey rectangle.
3. **Visible breaks in the descender.** Keep the horizontal child connector thin and centred so the vertical descender looks continuous.
4. **Inconsistent line weights.** Use the same `strokeWidth` for marriage lines, descenders, child connectors, and child lines.
5. **Ambiguous parentage.** It must be visually obvious which children belong to which couple. Use separate child connectors per marriage.

## Renderer / export pitfalls

- **`shape=line;direction=south` may be ignored by some PNG/SVG export renderers** (e.g. `tomkludy/drawio-renderer`), which render the cell as a horizontal line regardless of `direction`. When this happens, vertical descenders and child lines disappear or become misaligned horizontal segments. If the exported image shows missing vertical connectors, replace the vertical `shape=line` cells with thin `shape=rect` cells:

  ```xml
  <!-- Vertical descender rendered reliably as a 2-unit-wide rectangle -->
  <mxCell id="v1" value="" style="shape=rect;whiteSpace=wrap;html=1;fillColor=#333333;strokeColor=none;" vertex="1" parent="1">
    <mxGeometry x="469" y="65" width="2" height="45" as="geometry" />
  </mxCell>
  ```

  Overlap each vertical rectangle by one unit with the horizontal line it meets so the junction is continuous in raster output.

- **Exported SVG has a transparent background by default.** Insert a white background rectangle as the first child of the root `<g>` after export:

  ```xml
  <rect x="-0.5" y="-0.5" width="<pageWidth>" height="<pageHeight>" fill="#ffffff" stroke="none"/>
  ```

- **Exported PNG may carry an alpha channel even when the page background is white.** Some viewers/platforms treat it as transparent. Flatten the PNG to RGB with a white background after export (e.g. composite the alpha channel onto `#ffffff` and save as RGB).

- **Very wide charts may fail to render at `scale=2`.** The renderer can time out or return an empty file for charts wider than ~50,000 px at 2× scale. If `convert_file?scale=2` produces a 0-byte PNG, fall back to `scale=1` for the PNG. The SVG and `.drawio` source remain full resolution and zoomable.

- **Wide descendant charts are hard to read in messaging apps.** An all-descendants chart can easily exceed 8,000 px wide. The PNG preview will be downscaled in chat clients, making names unreadable. Always deliver the `.drawio` source and an SVG alongside the PNG, and tell the user the SVG/drawio files are the readable versions. See `references/descendant-chart-delivery.md` for a verification recipe and sample messaging wording.

- **Fallback: draw.io online export API.** If neither the local `drawio` CLI nor a localhost renderer is available, the public convert endpoint can render a draw.io XML file directly. It requires a `Referer` and `User-Agent` header or it returns 403:

  ```bash
  python3 - <<'PY'
  import urllib.request, urllib.parse
  with open('family_tree.drawio') as f:
      xml = f.read()
  data = urllib.parse.urlencode({
      'format': 'png',
      'xml': xml,
      'bg': '#FFFFFF',
      'border': '10',
      'scale': '2',
  }).encode('utf-8')
  req = urllib.request.Request('https://convert.diagrams.net/node/export', data=data, method='POST')
  req.add_header('Content-Type', 'application/x-www-form-urlencoded')
  req.add_header('User-Agent', 'Mozilla/5.0')
  req.add_header('Referer', 'https://app.diagrams.net/')
  with urllib.request.urlopen(req, timeout=60) as resp:
      open('family_tree.png', 'wb').write(resp.read())
  PY
  ```

  Always set `bg` explicitly (`#FFFFFF` for white), because the endpoint defaults to transparent. Use this as a fallback only — it sends the diagram XML to a third-party service.

## Visual verification

A chart can pass the structural linter and still look wrong. See `references/visual-verification.md` for:

- Pixel-level inspection recipes using Python/PIL when browser/vision tools fail to render the image.
- How to detect absurdly long horizontal connectors or suspiciously short vertical child drops.
- How to check whether a line actually overlaps a rendered name.
- The rule: **trust the rendered image and the user's eye over the linter.**

## Visitation-book style variant

For historical heraldic visitation books (e.g. *The Visitation of the County Palatine of Lancaster*, 1613), use the same orthogonal geometry but:

- **No boxes around names**: render each person as a plain top-aligned text label (`style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=top;..."`). Top alignment keeps each generation at a consistent y and prevents long names from overlapping connector lines above.
- **Compact layout**: smaller labels, tighter vertical spacing, use the page width efficiently.
- **Double-line marriage connectors**: two parallel horizontal `shape=line` elements between spouses.
- **Vertical lines meet the names**: child-drop lines terminate at the **top edge** of each text label so they do not cut through the text. Descenders and horizontal child connectors sit just above the names.

Draw the double marriage line as two `shape=line;direction=east` segments, typically 6–8 SVG units apart:

```xml
<mxCell id="m1a" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
  <mxGeometry x="450" y="58" width="40" height="1" as="geometry" />
</mxCell>
<mxCell id="m1b" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
  <mxGeometry x="450" y="65" width="40" height="1" as="geometry" />
</mxCell>
```

**Pitfall:** some draw.io PNG export renderers collapse closely-spaced parallel lines into a single line. The editable draw.io diagram and SVG export will show the double lines correctly. If the user needs the PNG preview to emphasise the double line, increase the spacing between the two lines or use a thicker stroke.

## Iteration rules

When the user gives feedback:
- Apply the smallest possible XML change.
- Do not rewrite the whole diagram unless they explicitly ask to restart.
- If a change makes it worse and they ask to revert, restore the last working version before trying something new.
- **Always verify the rendered image visually, not just with the linter.** A clean `validate.py` result (`0 error(s), 0 warning(s)`) does not mean the chart looks right. Browser vision and auxiliary vision models can fail on very wide charts or hallucinate details; use the pixel-level recipes in `references/visual-verification.md` when you cannot inspect the image directly.
- **Trust the user's visual judgment.** If they say a chart "doesn't look good enough" or that a line "still overlaps" a name, the rendered image is the authority. Adjust geometry and re-render until the image looks balanced to a human eye.
- **Do not argue from coordinate math when the user reports a visible defect.** If you cannot see the chart, render it, crop the affected area, and inspect the pixels. Geometry that says "no overlap" can still produce a rendered image that looks crowded or wrong.
- **Avoid hand-editing generated `.drawio` XML with regex when the source GEDCOM is unavailable.** If the GEDCOM has been cleaned from the cache, the generated XML is the only source of truth. Regex replacements on that XML are error-prone and can silently corrupt the file (orphaned geometry tags, duplicated attributes, lost cell wrappers). Either regenerate from the original GEDCOM, or if the GEDCOM is truly gone, ask the user to re-upload it before making geometry changes.
- When in doubt, ask exactly which element they want changed rather than guessing.

## GEDCOM-based trees

When the user supplies a GEDCOM file, prefer the reusable generator rather than hand-coding coordinates.

### Generator

`scripts/generate_visitation_tree.py` handles:

- An arbitrary focus person (`--root "Given Surname"` or `--root-id "@I123@"`).
- `N` generations of ancestors and descendants (`--generations N`).
- All descendants (`--all-descendants`, which auto-detects the deepest descendant generation).
- Descendant-only mode (`--descendants-only`, skips ancestors).
- Ancestor-only mode (`--ancestors-only`, skips descendants; shows focus person + ancestors).
- Multiple spouses per person, with children correctly ascribed to the marriage that produced them.
- Siblings and single-child couples.
- A recursive, bottom-up layout for descendant-only trees that guarantees no text-label overlaps (the chart simply grows wider where it needs to).

**Pitfall:** ancestor-only charts are not descendant charts run in reverse. The same connector logic that staggers horizontal child connectors per spouse produces overlapping horizontal segments in ancestor mode, because many units in an ancestor generation can sit close enough that full-width parent-spanning connectors overlap. Use the dedicated recursive ancestor generator (`scripts/generate_ancestor_tree_recursive.py`), which builds the tree bottom-up and draws a single vertical descender from each couple's marriage line straight down to the child. See `references/ancestor-chart-edge-case.md` for the full failure mode and fix.

Example:

```bash
python3 scripts/generate_visitation_tree.py \\
    --gedcom "family.ged" \\
    --root-id "@I18915667319@" \\
    --all-descendants \\
    --descendants-only \\
    --output tree.drawio
```

For an ancestor-only chart, use the recursive bottom-up generator:

```bash
python3 scripts/generate_ancestor_tree_recursive.py \\
    --gedcom "family.ged" \\
    --root-id "@I18910540946@" \\
    --generations 5 \\
    --output ancestors.drawio
```

- `--root-id` is the focus person (Adam, in this case).
- `--generations` controls depth. 5 generations is book-page friendly; 8 is very wide; 12+ becomes a navigable poster in draw.io.
- The focus person's spouse is shown at the bottom, but only the focus person's ancestors are drawn.
- Each couple gets a double marriage line and a single vertical descender to the child below.

### Layout limitations

- The focus person may not sit at the exact geometric centre if they have siblings, because the horizontal child connector is centred under the parents' marriage line. Do not break the orthogonal geometry to force the focus person into the centre.
- When two people from different families marry (e.g. Alexander Short & Elsie Finigan), their parents' units can overlap. The generator widens the marriage gap between the couple so each parent unit can descend cleanly to its own child. This is the intended behaviour for intermarried ancestor couples.
- Very large descendant charts become poster-wide; this is unavoidable if every name is to remain readable and every branch is kept contiguous. For book pages, split the tree by branch rather than squeezing.
- **Root with siblings in descendants-only mode.** If the focus person has siblings in the GEDCOM, the generator must not switch to the mixed/hourglass layout path. `generate_visitation_tree.py` now only collects `sibling_units` when ancestors are included. If you see a descendant chart with conjoined families, crossed connector lines, and many validator warnings, check whether the root has siblings and whether the recursive descendant layout was used. See `references/descendant-layout-y-position-bug.md`.
- The structural linter may still report "overlaps" between connected line segments (a horizontal child connector and the vertical drops that meet it, or multiple marriage lines that share the blood-person endpoint). These are intentional junctions, not text-label overlaps. In a **descendant chart**, however, warnings about overlapping `h*` / `v*` / `c*` segments between different family units indicate real conjoining and must be fixed.
- For ancestor charts, use `generate_ancestor_tree_recursive.py`. It builds bottom-up, keeps the focus person centred, and draws a single vertical descender from each couple's marriage line to the child below. Do not tolerate validator warnings between two `v*` line segments: they indicate duplicate parent→child segments that were not deduplicated, or adjacent couples whose descenders collide. The expected result is `0 error(s), 0 warning(s)`.
- **Mixed ancestor/descendant charts need separate ancestor connector logic.** In an hourglass chart, a married child couple (e.g. Alexander Short & Elsie Finigan) is linked from two parent units above. The descendant-style connector (horizontal bar from parent marriage centre to the child unit's blood-person centre) will join the two parent couples visually and create duplicate or misplaced drops. Mixed charts must draw ancestor links with **per-child-person connectors**: vertical descender from the parent couple, horizontal line to the specific child person's centre, then vertical drop. `generate_visitation_tree.py` tracks the mapping via `FamilyUnit.child_centers`. Any validator warning about overlapping `c*`, `ah*` or `av*` segments in a mixed chart means the per-child-person logic is missing or the stored centres were not shifted with the diagram. See `references/mixed-chart-connector-fix.md`.

- **Mixed charts should centre the ancestor block over the root generation.** The bottom-up ancestor layout centres each grandparent couple over its own child person in the married child couple. Without a final block shift, the parent couple can end up visually off-centre (e.g. shifted right when the focus person has a sibling far to one side). After the ancestor layout, shift the whole ancestor block so the lowest ancestor generation's unit midpoint aligns with the midpoint of the root generation's blood children. See `references/mixed-chart-layout.md`.

- **Root-generation siblings must be rendered, not just linked.** The ancestor layout links parents to every child person in the current generation, including siblings of the focus person. If those sibling units are not included in the flat rendered unit list, their connector lines are emitted without text labels, producing dangling vertical lines.
- The recursive ancestor generator grows exponentially in width with depth until pedigree collapse and missing ancestors curb it. 5 generations is compact; 8 is poster-wide; 12+ is generally only usable inside draw.io with pan/zoom.

### Manual workflow (when the generator needs tweaking)

1. Locate the cached `.ged` file (usually under `~/.hermes/cache/documents/`).
   ```bash
   find /home/tv/.hermes/cache/documents -type f -name '*.ged' -o -name '*gedcom*'
   ```
2. Parse it with `scripts/parse_gedcom.py` or the pattern in `references/gedcom-to-visitation-tree.md`.
3. Walk `FAMC` links upward for ancestors and `FAMS`/`CHIL` links downward for descendants.
4. Lay out generations with the same connector grammar used for hand-built trees.
5. Render and validate with `scripts/validate.py`.

### Layout and tuning

The generator is tuned for compact book-page output by default:

- Person label width: `TEXT_W = 75`
- Person label heights: `TEXT_H = 30`, `TEXT_H_SMALL = 28` (smallest generation)
- Marriage gap: `MARRIAGE_GAP = 14`
- Minimum gap between sibling units: `MIN_SIBLING_GAP = 12`
- Generation height: `GENERATION_HEIGHT = 105`
- Double marriage line offset/gap: `MARRIAGE_Y_OFFSET = 18`, `MARRIAGE_LINE_GAP = 3`
- **Desired descender length is per group**: **45 px for single-parent groups**, **63 px for couple groups**. The horizontal child-bar base for a unit is set to the highest required end among its groups, then each group to the left is staggered 4 px lower. This keeps couple-only sections unchanged while giving single-parent descenders a shorter, cleaner drop.
- Stagger between connectors of different spouses: **4 px**. A smaller stagger keeps left-hand groups from dropping back too close to their children's names.
- **Single-parent vertical descenders start **20 px below the bottom of the parent text box** (`descender_top = y + TEXT_H + 20.0`), not at the text centre, so the line clearly begins below the name.
- Vertical drops from the sibling bar run **up to the child's label** (`child.y - connector_y` in the generator) and are hidden by the white background rect. This removes the tiny 3–4 px break that otherwise appears above each name, which is especially noticeable for an only child in the last generation.
- Stagger between connectors of different spouses: **4 px**. A smaller stagger keeps left-hand groups from dropping back too close to their children's names.
**Pitfall — child drops can look broken just above a name.** If a vertical drop stops 3–4 px above the child's label, the gap can read as a break, especially for an only child in the last generation where there is no horizontal sibling bar to mask it. The fix is **not** to run the drop into the label; instead, **extend the parent descender 1 px below the horizontal child-bar** (`vline(..., connector_y + 1.0 - descender_top)`). When a sibling bar is present it hides the 1 px extension; when it is absent (only child), the extension meets the child drop and closes the gap. Keep the child drop starting at `connector_y + 1.0` and ending at `child.y - 4.0`. Update the structural linter to ignore the intentional overlaps between the child-drop line, the horizontal/vertical connector segments it meets, and the label background only when the drop genuinely terminates at the label top.

**Pitfall — child drops can become too short.** With the drop running up to the label, the visible portion is roughly **17–21 px**, which is long enough to read as a deliberate connector. If the rendered drops look like tiny floating ticks, the horizontal bar has been raised too far; increase the connector base offset slightly. If they look long enough but the names still feel crowded, see the next pitfall.

**Pitfall — child names look crowded or obscured by the sibling bar.** If the horizontal child connector feels too close to the names below it — so that the descender from the bar seems to crowd or overlap the text visually — the fix is to **raise the bar**, not to lower the child text. Shorten the long vertical descender from the parent's marriage line by reducing the connector base offset (e.g. from 55 px to 45 px). If multiple spouses produce staggered left-hand groups, reduce `CHILD_CONNECTOR_STAGGER` as well (e.g. from 6 px to 4 px) so those groups do not drop back into the names. Verify the rendered image, not just the linter.

**Pitfall — parent names look cut or overlapped by the child connector.** If vertical descenders from a parent or the horizontal child bars feel too close to parent names, first ensure every label has an explicit white background rect drawn behind it. Then tune geometry: for single parents, lower the descender start (`descender_top = y + TEXT_H + 20.0`); for couples, lengthen the descender by increasing the desired couple length (default 63 px) or increasing `GENERATION_HEIGHT` to create more vertical room. Verify the rendered image.

**Pitfall — horizontal connectors can dominate the chart.** When one parent's children have very wide subtrees, the horizontal connector for that marriage can stretch thousands of pixels. The layout is technically correct, but visually it can make the tree look lopsided. If this happens, check whether siblings are spaced farther apart than necessary (`MIN_SIBLING_GAP`) or whether a branch could be split onto a separate page.

The output page is auto-fitted to the content bounding box with a small margin, so there is no extra whitespace around the tree. If you need the chart smaller still, reduce these constants; if text starts to wrap or lines touch, you have gone too far.

### Support files

- `references/pre-delivery-checklist.md` — step-by-step checklist: generate, render, run `verify_family_tree.py`, visually inspect, and deliver.
- `references/descendant-chart-delivery.md` — delivering wide all-descendant charts: expected dimensions, readable formats, and a GEDCOM verification recipe.
- `references/child-drop-continuity-fix.md` — why child drops now run up to the label and which validator overlaps to ignore.
- `references/single-vs-couple-descenders.md` — exact descender geometry for single-parent vs couple groups and why per-group desired lengths are used.
- `references/visual-verification.md` — how to inspect a rendered chart when vision tools fail, including pixel-level recipes and what "looks wrong" means beyond the linter.
- `references/gedcom-to-visitation-tree.md` — full GEDCOM-to-tree workflow and layout algorithm.
- `references/ancestor-chart-edge-case.md` — why ancestor-only charts need a dedicated bottom-up generator and how it differs from descendant charts.
- `references/mixed-chart-connector-fix.md` — mixed (hourglass) charts: per-child-person ancestor connectors, sibling rendering, and the `child_centers` shift.
- `references/descendant-layout-y-position-bug.md` — debugging a descendant-only chart that collapses onto a single horizontal line, the root-has-siblings pitfall, and verification recipes.
- `references/skill-extraction.md` — how to extract this skill from its original nested location under `drawio-skill` into a standalone GitHub repository.
- `scripts/verify_family_tree.py` — automated pre-delivery check: runs the linter, verifies generational separation, and detects overlapping horizontal child connectors.
- `references/visitation-style-family-tree.md` — clean three-generation tree using `shape=line` connectors.
- `references/minimal-family-tree.md` — minimal worked example.
- `scripts/parse_gedcom.py` — reusable minimal GEDCOM parser.
- `scripts/generate_visitation_tree.py` — GEDCOM to draw.io XML generator (descendants and hourglass trees).
- `scripts/generate_ancestor_tree_recursive.py` — dedicated bottom-up ancestor chart generator.
- `scripts/generate_vertical_pedigree.py` — direct-line vertical pedigree generator.
- `scripts/flatten_export.py` — render `.drawio` to PNG/SVG via localhost:8080, inject white SVG background, and flatten PNG alpha.

## Vertical direct-line pedigree

For a top-to-bottom chart showing only the direct ancestors between two people (no siblings, cousins, aunts, or uncles), use the vertical pedigree generator:

```bash
python3 scripts/generate_vertical_pedigree.py \\
    --gedcom "family.ged" \\
    --from "Adam Short" \\
    --to "Edward III Plantagenet" \\
    --output pedigree.drawio
```

- `--from` is the focus/descendant; `--to` is the target ancestor.
- Accepts names (partial match) or `@I...` IDs.
- Each row shows the direct ancestor and spouse side by side, with a double marriage line and a vertical descent line to the child below.
- The focus person appears alone at the bottom.
- Validates with the same `validate.py` linter.

Example output: Edward III → John of Gaunt → Joan Beaufort → ... → Adam Short, 22 generations, 0 errors / 0 warnings.
