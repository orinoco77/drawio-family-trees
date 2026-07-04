# Visual verification for generated family trees

The structural linter (`validate.py`) only catches hard overlaps between leaf vertices and malformed edges. It will happily report `0 error(s), 0 warning(s)` for a chart that still looks wrong to a human — for example:

- a horizontal child connector that stretches thousands of pixels because children are placed far apart;
- vertical drops to children that are so short they look like ticks instead of connectors;
- a raised marriage line whose descender disappears behind the white text boxes, creating a visual disconnect;
- labels that are technically clear of lines but still look crowded.

Do not treat a clean linter result as proof that the chart is good. Always verify the rendered image visually.

## When vision tools fail

Browser-based vision and auxiliary vision models can fail to render very wide PNGs or SVGs, or may hallucinate details. If the vision tools cannot show you the chart, fall back to pixel-level inspection with Python/PIL.

### ASCII preview of a region

```python
from PIL import Image

img = Image.open('family_tree.png').convert('L')
# Crop a region in PNG pixels (SVG coords × scale)
region = img.crop((x_left, y_top, x_right, y_bottom))

arr = region.load()
for y in range(region.height):
    row = ''.join(
        '#' if arr[x, y] < 100 else '.' if arr[x, y] < 200 else ' '
        for x in range(region.width)
    )
    print(row)
```

Use this to check:
- whether a vertical child drop actually reaches near (but not into) a name;
- whether a marriage line sits where you expect relative to the text;
- whether horizontal connectors are disproportionately long;
- whether any dark pixels intrude into text boxes.

### Detect unusually long horizontal connectors

```python
import re
with open('family_tree.svg') as f:
    svg = f.read()

for m in re.finditer(r'<path d="M ([0-9.]+) ([0-9.]+) L ([0-9.]+) ([0-9.]+)"', svg):
    x1, y1, x2, y2 = map(float, m.groups())
    if y1 == y2 and abs(x2 - x1) > 1000:
        print(f'horizontal line y={y1}: length {abs(x2-x1):.0f}')
```

A connector that spans most of the page width is not necessarily a bug — it happens when one parent's children have very wide subtrees — but it is a strong signal that the layout may look unbalanced or that children are spaced too far apart.

### Detect short vertical child drops

```python
import xml.etree.ElementTree as ET

tree = ET.parse('family_tree.drawio')
for cell in tree.iter('mxCell'):
    style = cell.get('style', '')
    geom = cell.find('mxGeometry')
    if geom is None:
        continue
    if 'shape=rect' in style:
        h = float(geom.get('height', 0))
        w = float(geom.get('width', 0))
        if h > w * 3 and h < 15:  # tall, thin rect shorter than 15 units
            print(f'short vertical segment at ({geom.get("x")}, {geom.get("y")}) height={h}')
```

Vertical drops much shorter than the text-box height tend to look disconnected. Drops should generally end a small, consistent gap (3–6 units) above the child's label.

### Check rendered overlap pixels

```python
from PIL import Image
import numpy as np

img = Image.open('family_tree.png').convert('L')
arr = np.array(img)

# Example: inspect the area just above a child's name box
x_svg, y_svg = 168, 122  # child label top-left in SVG coords
scale = 2
x, y, w, h = x_svg * scale, y_svg * scale, 75 * scale, 30 * scale
region = arr[y-10:y+h, x:x+w]
dark = np.sum(region < 200)
print(f'dark pixels in buffer above label: {dark}')
```

## What to look for

1. **Marriage line position.** The double line should sit at the visual centre/baseline of the spouse labels — not so low that the names appear to float above it, not so high that it looks like a strikethrough. Because labels are drawn on top with a white fill, a line inside the text box's vertical range is hidden; verify in the rendered image that the visible segment in the spouse gap is at a comfortable height.

2. **Descender continuity.** The vertical descender from the marriage line to the child connector should read as one continuous line. If the marriage line is raised inside the text box, the segment behind the labels is hidden; check that the visible part below the labels still looks connected to the marriage line in the gap.

3. **Child-name-to-bar spacing.** The horizontal sibling bar should sit clearly above the child names, with enough vertical room that the descender from the bar does not crowd the text. If the bar feels too close, raise it by shortening the long vertical descender from the parent's marriage line (do **not** lower the child text). In the generator this means reducing the connector base offset (e.g. from 45 px to 35 px) and, if staggered left-hand groups are also too close, reducing `CHILD_CONNECTOR_STAGGER` (e.g. from 6 px to 4 px).

4. **Child-drop length.** Drops should be long enough to look intentional (typically at least half the label height) and should stop a consistent small distance above the label. Too short and they look broken; too long and they overlap or crowd the names.

5. **Horizontal connector proportion.** Connectors should span a parent's children, not the whole chart. If one connector is an order of magnitude longer than the others, reconsider whether children are spaced correctly or whether a different layout would group siblings more tightly.

6. **Horizontal connector overlap in descendant charts.** Different parent units in the same generation should not have horizontal child connectors that overlap horizontally at the same or nearly the same y-level. Overlaps make unrelated families look conjoined and are the most common visual defect after the y-position bug. Use the automated check in `scripts/verify_family_tree.py`, or run this recipe:

   ```python
   import xml.etree.ElementTree as ET

   tree = ET.parse('family_tree.drawio')
   h_lines = []
   for cell in tree.iter('mxCell'):
       cell_id = cell.get('id', '')
       style = cell.get('style', '')
       geom = cell.find('mxGeometry')
       if geom is None or 'shape=line;direction=east' not in style:
           continue
       x = float(geom.get('x', 0))
       y = float(geom.get('y', 0))
       w = float(geom.get('width', 0))
       if cell_id.startswith('h') and w > 5:
           h_lines.append((cell_id, y, x, x + w))

   overlaps = []
   for i, (id1, y1, x1a, x1b) in enumerate(h_lines):
       for j, (id2, y2, x2a, x2b) in enumerate(h_lines):
           if i >= j:
               continue
           if abs(y1 - y2) <= 3.0 and not (x1b < x2a or x2b < x1a):
               overlaps.append((id1, id2))

   if overlaps:
       print('Overlapping connectors (families conjoined):')
       for a, b in overlaps:
           print(f'  {a} overlaps {b}')
   else:
       print('No overlapping connectors.')
   ```

   A clean descendant chart should report no overlapping connectors. If overlaps exist, the layout is probably using the wrong code path (for example, the root has siblings and the mixed-mode layout was selected instead of the recursive descendant layout). See `references/descendant-layout-y-position-bug.md`.

7. **Human-first judgment.** When the user says a chart "doesn't look good enough," trust that over a clean linter result. Iterate on the geometry until the rendered image looks balanced, not until a numeric check passes.

## Child names crowded by the sibling bar — case study

This is a common defect that the linter will not catch. The horizontal child connector sits so close to the names below it that the vertical drops appear to crowd or partially obscure the text, even though the drops technically end a few pixels above the labels.

**Rendered symptom:** the gap between the horizontal bar and the top of the child name looks cramped; the descenders from the bar look like they are sitting on the text.

**Coordinate symptom:** the sibling bar is only ~12–15 px above the child text.

**Fix:** raise the bar by shortening the long parent-to-bar descender.

```python
# In generate_visitation_tree.py
base_connector_y = max(max_descender_top + 35.0, unit.y + TEXT_H + 35.0)  # was 45.0
CHILD_CONNECTOR_STAGGER = 4.0  # was 6.0; keeps staggered left groups clear
```

After the change the bar should sit roughly **21–25 px** above the child names, and the vertical drops should be **17–21 px** long — long enough to look deliberate, short enough to stop cleanly above the labels.

**Verification recipe:**

```python
from PIL import Image
import numpy as np

img = Image.open('family_tree.png').convert('L')
arr = np.array(img)
scale = img.height / 708  # SVG viewBox height for this chart

# Sibling bar and child text for a typical generation
bar_y_svg = 111   # horizontal child connector y
text_y_svg = 132  # child label y

gap_px = (text_y_svg - bar_y_svg) * scale
print(f'bar-to-text gap: {gap_px:.1f} px')
# Expect roughly 20–25 px after the fix.
```

If the gap is below ~18 px, raise the bar further. If the gap is above ~30 px, the drops may start to look too long; lower the bar slightly.
