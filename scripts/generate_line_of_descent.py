#!/usr/bin/env python3
"""
Line-of-descent family tree with siblings.

Given a GEDCOM file and an ordered list of person IDs forming a direct
bloodline (top ancestor -> ... -> target), produce a compact visitation-style
diagram that shows, at each generation, the full sibling group of the person
who continues the line. Siblings are not expanded further.
"""

from __future__ import annotations

import argparse
import html
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_gedcom import get_birth, get_name, parse_gedcom
from drawio_layout import (
    CHILD_DROP,
    DEFAULT_TEXT_H,
    MARGIN,
    MARRIAGE_GAP,
    MARRIAGE_LINE_GAP,
    MARRIAGE_Y_OFFSET,
    SIBLING_GAP,
    TEXT_W,
    TITLE_Y,
    child_y_from_connector,
    compute_max_label_height,
    connector_y_from_parent,
    couple_descender_top,
    hline,
    single_descender_top,
    text_cell,
    vrect,
)


def build_unit(person_id: str, line_child_id: str, individuals: dict, families: dict):
    """Return local layout for the family unit of `person_id` whose child is
    `line_child_id`. Local origin has the ancestor label at x=0."""
    famc = individuals.get(line_child_id, {}).get("famc", "")
    fam = families.get(famc)
    if not fam:
        raise ValueError(f"No family of origin found for line child {line_child_id}")

    spouse_id = None
    if fam.get("husb") == person_id:
        spouse_id = fam.get("wife")
    elif fam.get("wife") == person_id:
        spouse_id = fam.get("husb")
    else:
        raise ValueError(
            f"Person {person_id} is not a parent of {line_child_id} in family {famc}"
        )

    children = fam.get("chil", [])
    if line_child_id not in children:
        raise ValueError(f"Line child {line_child_id} not in family {famc} children")

    root_x = 0.0
    spouse_x = TEXT_W + MARRIAGE_GAP
    n = len(children)
    children_width = n * TEXT_W + max(0, n - 1) * SIBLING_GAP
    couple_center = (root_x + spouse_x + TEXT_W) / 2.0
    children_left = couple_center - children_width / 2.0
    child_xs = [children_left + j * (TEXT_W + SIBLING_GAP) for j in range(n)]
    line_idx = children.index(line_child_id)

    return {
        "person_id": person_id,
        "spouse_id": spouse_id,
        "children": children,
        "child_xs": child_xs,
        "line_idx": line_idx,
        "root_x": root_x,
        "spouse_x": spouse_x,
    }


def ensure_spouse_room(child_xs: list[float], line_idx: int) -> list[float]:
    """Make sure there is horizontal room to the right of the line child for
    the next unit's spouse label.  Returns a new child_xs list."""
    if line_idx >= len(child_xs) - 1:
        return child_xs
    required = TEXT_W + MARRIAGE_GAP + TEXT_W + SIBLING_GAP
    current_gap = child_xs[line_idx + 1] - child_xs[line_idx]
    if current_gap >= required:
        return child_xs
    extra = required - current_gap
    return [
        x if j <= line_idx else x + extra
        for j, x in enumerate(child_xs)
    ]


def generate(gedcom_path: str, line_ids: list[str], output: str,
             title: str | None = None, font_family: str = "Helvetica"):
    individuals, families = parse_gedcom(gedcom_path)

    # Validate line
    for lid in line_ids:
        if lid not in individuals:
            raise ValueError(f"Individual {lid} not found in GEDCOM")
    for i in range(len(line_ids) - 1):
        parent = line_ids[i]
        child = line_ids[i + 1]
        famc = individuals[child].get("famc", "")
        fam = families.get(famc)
        if not fam or (fam.get("husb") != parent and fam.get("wife") != parent):
            raise ValueError(
                f"{child} is not a child of {parent} (family {famc})"
            )

    units = []
    for i in range(len(line_ids) - 1):
        unit = build_unit(line_ids[i], line_ids[i + 1], individuals, families)
        units.append(unit)

    # Make room for each next unit's spouse to the right of the line child.
    for i, unit in enumerate(units[:-1]):
        unit["child_xs"] = ensure_spouse_room(unit["child_xs"], unit["line_idx"])

    # Compute horizontal offsets so each line child aligns with the next unit's ancestor.
    offsets = [0.0] * len(units)
    # Bottom unit: start at MARGIN
    offsets[-1] = MARGIN
    for i in range(len(units) - 2, -1, -1):
        # unit i's line child x + offset_i == unit i+1's ancestor x + offset_{i+1}
        # unit i+1 ancestor local x is 0
        offsets[i] = offsets[i + 1] - units[i]["child_xs"][units[i]["line_idx"]]

    # Shift everything so leftmost element is at MARGIN
    min_x = math.inf
    for i, unit in enumerate(units):
        ox = offsets[i]
        xs = [ox + unit["root_x"], ox + unit["spouse_x"] + TEXT_W]
        xs.extend(ox + cx for cx in unit["child_xs"])
        xs.extend(ox + cx + TEXT_W for cx in unit["child_xs"])
        min_x = min(min_x, *xs)
    shift = MARGIN - min_x
    offsets = [o + shift for o in offsets]

    # --- Dynamic height calculation ------------------------------------------
    chart_ids = set(line_ids)
    for unit in units:
        chart_ids.add(unit["person_id"])
        if unit["spouse_id"]:
            chart_ids.add(unit["spouse_id"])
        chart_ids.update(unit["children"])

    max_label_h = compute_max_label_height(
        lambda iid: get_name(iid, individuals),
        lambda iid: get_birth(iid, individuals),
        chart_ids,
    )
    # -------------------------------------------------------------------------

    # Pre-compute y positions top-down.  Child labels are positioned relative to
    # the sibling bar, not the parent labels, so raising/lowering the bar raises
    #/lowers the children and keeps the child-name drops constant.
    root_y = MARGIN + TITLE_Y + 20
    for i, unit in enumerate(units):
        unit["root_y"] = root_y

        if unit["spouse_id"]:
            descender_top = couple_descender_top(root_y)
        else:
            descender_top = single_descender_top(root_y, max_label_h)

        unit["connector_y"] = connector_y_from_parent(descender_top, max_label_h)
        unit["child_y"] = child_y_from_connector(unit["connector_y"])

        # The line child becomes the root of the next unit.
        root_y = unit["child_y"]

    cells = []
    lines = []
    labels = []
    parent_id = 1
    max_x = 0.0
    max_y = 0.0

    # Title (drawn first, behind labels if any overlap)
    if title:
        title_w = 600.0
        title_x = MARGIN
        cells.append(
            f'<mxCell id="title" value="{html.escape(title)}" style="text;html=1;strokeColor=none;'
            f'fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;'
            f'fontSize=14;fontColor=#333333;fontFamily={html.escape(font_family)};fontStyle=1;" '
            f'vertex="1" parent="{parent_id}">\n'
            f'  <mxGeometry x="{title_x:.2f}" y="{TITLE_Y:.2f}" width="{title_w:.2f}" height="20" as="geometry"/>\n'
            f'</mxCell>'
        )

    for i, unit in enumerate(units):
        ox = offsets[i]
        root_y = unit["root_y"]
        connector_y = unit["connector_y"]
        child_y = unit["child_y"]

        # Marriage lines and vertical descender (drawn before labels)
        if unit["spouse_id"]:
            m1x = ox + unit["root_x"] + TEXT_W
            mwidth = unit["spouse_x"] - (unit["root_x"] + TEXT_W)
            m1y = root_y + MARRIAGE_Y_OFFSET
            lines.append(hline(str(parent_id), f"u{i}_m1", m1x, m1y, mwidth))
            lines.append(hline(str(parent_id), f"u{i}_m2", m1x, m1y + MARRIAGE_LINE_GAP, mwidth))

            centre_x = m1x + mwidth / 2.0 - 1.0
            descender_top = couple_descender_top(root_y)
            lines.append(vrect(str(parent_id), f"u{i}_vd", centre_x, descender_top,
                               connector_y - descender_top))
        else:
            centre_x = ox + unit["root_x"] + TEXT_W / 2.0 - 1.0
            descender_top = single_descender_top(root_y, max_label_h)
            lines.append(vrect(str(parent_id), f"u{i}_vd", centre_x, descender_top,
                               connector_y - descender_top))

        # Horizontal child connector and child drops
        if unit["children"]:
            left_x = ox + unit["child_xs"][0] + TEXT_W / 2.0 - 1.0
            right_x = ox + unit["child_xs"][-1] + TEXT_W / 2.0 + 1.0
            lines.append(hline(str(parent_id), f"u{i}_hc", left_x, connector_y, right_x - left_x))

            for j, cid in enumerate(unit["children"]):
                cx = ox + unit["child_xs"][j]
                drop_x = cx + TEXT_W / 2.0 - 1.0
                # Child drop: stop just above the child's label top.
                drop_h = child_y - connector_y - 4.0
                lines.append(vrect(str(parent_id), f"u{i}_cd{j}", drop_x, connector_y + 1.0, drop_h))

        # Person and spouse labels (drawn on top of connector lines)
        labels.append(text_cell(
            str(parent_id), f"u{i}_root", ox + unit["root_x"], root_y, TEXT_W, max_label_h,
            get_name(unit["person_id"], individuals),
            get_birth(unit["person_id"], individuals), font_family
        ))
        max_x = max(max_x, ox + unit["root_x"] + TEXT_W)

        if unit["spouse_id"]:
            labels.append(text_cell(
                str(parent_id), f"u{i}_spouse", ox + unit["spouse_x"], root_y, TEXT_W, max_label_h,
                get_name(unit["spouse_id"], individuals),
                get_birth(unit["spouse_id"], individuals), font_family
            ))
            max_x = max(max_x, ox + unit["spouse_x"] + TEXT_W)

        # Child labels (skipped for intermediate line children)
        if unit["children"]:
            for j, cid in enumerate(unit["children"]):
                cx = ox + unit["child_xs"][j]
                is_line_child = (j == unit["line_idx"])
                if not (is_line_child and i < len(units) - 1):
                    labels.append(text_cell(
                        str(parent_id), f"u{i}_child{j}", cx, child_y, TEXT_W, max_label_h,
                        get_name(cid, individuals), get_birth(cid, individuals), font_family
                    ))
                max_x = max(max_x, cx + TEXT_W)

        max_y = max(max_y, child_y + max_label_h)

    cells.extend(lines)
    cells.extend(labels)

    page_w = max_x + MARGIN
    page_h = max_y + MARGIN

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="1970-01-01T00:00:00.000Z"
        agent="Hermes drawio-family-trees" etag="lineofdescent" version="21.0.0" type="device">
  <diagram name="Page-1" id="line-of-descent">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1"
                  connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(math.ceil(page_w))}"
                  pageHeight="{int(math.ceil(page_h))}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{chr(10).join(cells)}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    with open(output, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Line of descent ({len(line_ids)} people, {len(units)} families) -> {output}")


def main():
    parser = argparse.ArgumentParser(description="Generate a line-of-descent family tree with siblings.")
    parser.add_argument("--gedcom", required=True, help="Path to GEDCOM file")
    parser.add_argument("--line", required=True,
                        help="Comma-separated list of @I...@ IDs from top ancestor to target")
    parser.add_argument("--output", required=True, help="Output .drawio file")
    parser.add_argument("--title", help="Diagram title")
    parser.add_argument("--font-family", default="Helvetica", help="Font family")
    args = parser.parse_args()

    line_ids = [x.strip() for x in args.line.split(",") if x.strip()]
    if len(line_ids) < 2:
        raise SystemExit("--line must contain at least two IDs")

    title = args.title or f"Line of descent: {get_name(line_ids[0], {})} to {get_name(line_ids[-1], {})}"
    generate(args.gedcom, line_ids, args.output, title=title, font_family=args.font_family)


if __name__ == "__main__":
    main()
