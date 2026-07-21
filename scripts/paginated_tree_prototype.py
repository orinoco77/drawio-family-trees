#!/usr/bin/env python3
"""Minimal paginated-family-tree prototype.

Demonstrates splitting a large descendant branch into page-sized draw.io
diagrams linked by numbered off-page continuation markers. Hard-codes a
small example (Thomas Finigan → James Finigan) as a starting point.

See references/paginated-family-trees.md for the convention.
"""

import html
from pathlib import Path

PAGE_W, PAGE_H, MARGIN = 794, 1123, 40
TEXT_W, TEXT_H = 80, 34
MARRIAGE_GAP, SIBLING_GAP, GEN_HEIGHT = 14, 16, 110


def esc_attr(v: str) -> str:
    return html.escape(v).replace('"', '&quot;')


def label(x, y, text, cid):
    return (
        f'<mxCell id="{cid}_bg" value="" style="shape=rect;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=none;" vertex="1" parent="1">'
        f'<mxGeometry x="{x:.2f}" y="{y:.2f}" width="{TEXT_W}" height="{TEXT_H}" as="geometry"/></mxCell>'
        f'<mxCell id="{cid}" value="{esc_attr(text)}" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=center;verticalAlign=top;whiteSpace=wrap;rounded=0;fontSize=11;fontFamily=Helvetica;fontColor=#333333;" vertex="1" parent="1">'
        f'<mxGeometry x="{x:.2f}" y="{y:.2f}" width="{TEXT_W}" height="{TEXT_H}" as="geometry"/></mxCell>'
    )


def hline(x, y, w, cid):
    return (f'<mxCell id="{cid}" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">'
            f'<mxGeometry x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="1" as="geometry"/></mxCell>')


def vrect(x, y, h, cid, w=2.0):
    return (f'<mxCell id="{cid}" value="" style="shape=rect;whiteSpace=wrap;html=1;fillColor=#333333;strokeColor=none;" vertex="1" parent="1">'
            f'<mxGeometry x="{x:.2f}" y="{y:.2f}" width="{w}" height="{h:.2f}" as="geometry"/></mxCell>')


def marker(x, y, num, cid):
    s = 22
    return (
        f'<mxCell id="{cid}_circle" value="" style="ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#ffffff;strokeColor=#333333;strokeWidth=1.5;" vertex="1" parent="1">'
        f'<mxGeometry x="{x:.2f}" y="{y:.2f}" width="{s}" height="{s}" as="geometry"/></mxCell>'
        f'<mxCell id="{cid}_num" value="{num}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=11;fontFamily=Helvetica;fontColor=#333333;" vertex="1" parent="1">'
        f'<mxGeometry x="{x:.2f}" y="{y:.2f}" width="{s}" height="{s}" as="geometry"/></mxCell>'
    )


def header(title, page):
    return (
        '<?xml version="1.0" encoding="UTF-8"?><mxfile host="app.diagrams.net" version="22.0.0">'
        '<diagram name="Page"><mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" page="1" pageScale="1" pageWidth="794" pageHeight="1123">'
        '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
        f'<mxCell id="title" value="{esc_attr(title)}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=14;fontFamily=Helvetica;fontColor=#333333;" vertex="1" parent="1">'
        f'<mxGeometry x="{MARGIN}" y="{MARGIN}" width="{PAGE_W-2*MARGIN}" height="24" as="geometry"/></mxCell>'
        f'<mxCell id="page_num" value="{esc_attr(page)}" style="text;html=1;strokeColor=none;fillColor=none;align=right;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=10;fontFamily=Helvetica;fontColor=#999999;" vertex="1" parent="1">'
        f'<mxGeometry x="{PAGE_W-MARGIN-60}" y="{PAGE_H-MARGIN-20}" width="60" height="20" as="geometry"/></mxCell>'
    )


def footer():
    return '</root></mxGraphModel></diagram></mxfile>'


def couple(cx, y, ltext, rtext, lid, rid, did):
    lx = cx - TEXT_W - MARRIAGE_GAP / 2
    rx = cx + MARRIAGE_GAP / 2
    out = label(lx, y, ltext, lid) + label(rx, y, rtext, rid)
    ly = y + 18
    out += hline(lx + TEXT_W, ly, MARRIAGE_GAP, f"{lid}_m1")
    out += hline(lx + TEXT_W, ly + 3, MARRIAGE_GAP, f"{lid}_m2")
    out += vrect(cx - 1, ly + 1.5, GEN_HEIGHT - 45, did)
    return out, cx, y + GEN_HEIGHT


def children(px, py, labels, ids, prefix, cont=None):
    cont = cont or {}
    n = len(labels)
    total = n * TEXT_W + (n - 1) * SIBLING_GAP
    sx = px - total / 2
    out = hline(sx, py, total, f"{prefix}_h")
    for i, (text, cid) in enumerate(zip(labels, ids)):
        x = sx + i * (TEXT_W + SIBLING_GAP)
        cx = x + TEXT_W / 2
        dl = GEN_HEIGHT - TEXT_H - 40
        out += vrect(cx - 1, py + 1, dl, f"{cid}_drop")
        ly = py + dl - 4
        out += label(x, ly, text, cid)
        if i in cont:
            my = ly + TEXT_H + 8
            out += vrect(cx - 1, ly + TEXT_H, my - (ly + TEXT_H), f"{cid}_md")
            out += marker(cx - 11, my, cont[i], cid)
    return out


def page1():
    xml = header("Descendants of Thomas Finigan — page 1", "1")
    cx = PAGE_W / 2
    y = MARGIN + 40
    xml += couple(cx, y, "Thomas Finigan\n(b. abt 1820)", "Mary\n(b. ?)", "t", "m", "td")[0]
    _, _, cy = couple(cx, y, "", "", "t", "m", "td")
    xml += children(cy - GEN_HEIGHT + GEN_HEIGHT, cy,
                    ["Ellen Finigan\n(b. ?)", "James Finigan\n(b. 1846)",
                     "Catherine Finigan\n(b. ?)", "John Finigan\n(b. ?)"],
                    ["e", "j", "c", "jo"], "tc", {1: "2"})
    return xml + footer()


def page2():
    xml = header("Descendants of James Finigan (b. 1846) — page 2", "2")
    cx = PAGE_W / 2
    my = MARGIN + 40
    xml += marker(cx - 11, my, "2", "r")
    xml += vrect(cx - 1, my + 22, 40, "rd")
    jy = my + 22 + 40 + 4
    xml += couple(cx, jy, "James Finigan\n(b. 1846)", "Margaret\n(b. ?)", "j", "ma", "jd")[0]
    _, _, cy = couple(cx, jy, "", "", "j", "ma", "jd")
    xml += children(cy - GEN_HEIGHT + GEN_HEIGHT, cy,
                    ["Thomas Finigan\n(b. ?)", "Mary Finigan\n(b. ?)", "Ann Finigan\n(b. ?)"],
                    ["c1", "c2", "c3"], "jc")
    return xml + footer()


def main():
    d = Path.cwd()
    (d / "page_1_thomas.drawio").write_text(page1(), encoding="utf-8")
    (d / "page_2_james.drawio").write_text(page2(), encoding="utf-8")
    print("Wrote page_1_thomas.drawio and page_2_james.drawio")


if __name__ == "__main__":
    main()
