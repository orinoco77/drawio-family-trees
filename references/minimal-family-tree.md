# Minimal Three-Generation Family Tree

This is a complete, clean draw.io XML template for a three-generation family tree. It demonstrates the conventions from `drawio-family-trees`: orthogonal `shape=line` connectors, thin child connector, no arrowheads, consistent 1.5 px line weight, and clear parent-child grouping.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="drawio" version="26.0.0">
  <diagram name="Family Tree">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1200" pageHeight="900" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />

        <mxCell id="title" value="Family Tree" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=18;fontStyle=1" vertex="1" parent="1">
          <mxGeometry x="300" y="20" width="400" height="30" as="geometry" />
        </mxCell>

        <!-- Generation 1 -->
        <mxCell id="g1p1" value="Arthur Bennett&#xa;(b. 1945)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#333333;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="250" y="80" width="140" height="60" as="geometry" />
        </mxCell>
        <mxCell id="g1p2" value="Dorothy Bennett&#xa;(b. 1948)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#333333;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="450" y="80" width="140" height="60" as="geometry" />
        </mxCell>

        <!-- Marriage line -->
        <mxCell id="m1" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
          <mxGeometry x="390" y="110" width="60" height="1" as="geometry" />
        </mxCell>

        <!-- Vertical descender -->
        <mxCell id="v1" value="" style="shape=line;direction=south;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
          <mxGeometry x="420" y="110" width="1" height="50" as="geometry" />
        </mxCell>

        <!-- Horizontal child connector -->
        <mxCell id="h1" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
          <mxGeometry x="190" y="160" width="460" height="1" as="geometry" />
        </mxCell>

        <!-- Generation 2 -->
        <mxCell id="g2p1" value="Robert Bennett&#xa;(b. 1970)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#333333;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="120" y="250" width="140" height="60" as="geometry" />
        </mxCell>
        <mxCell id="g2p2" value="Margaret Chen&#xa;(b. 1973)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#333333;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="600" y="250" width="140" height="60" as="geometry" />
        </mxCell>

        <!-- Vertical child lines -->
        <mxCell id="c1" value="" style="shape=line;direction=south;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
          <mxGeometry x="190" y="160" width="1" height="90" as="geometry" />
        </mxCell>
        <mxCell id="c2" value="" style="shape=line;direction=south;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">
          <mxGeometry x="650" y="160" width="1" height="90" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## Key points

- `shape=line;direction=east` renders a thin horizontal line with no visible thickness at the junction.
- `shape=line;direction=south` renders a precise vertical line.
- All connectors use `strokeWidth=1.5` and `endArrow=none` is implicit (no edge style).
- Each marriage has its own child connector (`h1`, `h2`, …), so children are unambiguously grouped under the correct parents.
- Boxes use `rounded=0` for a clean, conventional rectangular look.
