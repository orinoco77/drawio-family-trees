#!/usr/bin/env python3
"""Generate a vertical direct-line pedigree chart from GEDCOM.

Shows only the ancestors on the path from a focus person up to a target
ancestor, plus each ancestor's spouse.  No siblings, aunts, uncles, or cousins.
"""

import argparse
import re
import sys
from collections import deque
from pathlib import Path

TEXT_W = 110.0
TEXT_H = 38.0
MARRIAGE_GAP = 20.0
GENERATION_HEIGHT = 80.0
MARRIAGE_Y_OFFSET = 12.0
MARRIAGE_LINE_GAP = 4.0
STROKE_COLOR = "#333333"
MARGIN = 20.0
FONT_FAMILY = "Helvetica"  # default font; override with --font-family


def parse_gedcom(path: str):
    individuals: dict[str, dict] = {}
    families: dict[str, dict] = {}

    current_indi: str | None = None
    current_fam: str | None = None
    current_event: str | None = None

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line:
                continue
            parts = line.split(" ", 2)
            if len(parts) < 2:
                continue
            level = int(parts[0])
            rest = parts[1]
            value = parts[2] if len(parts) > 2 else ""

            if level == 0:
                current_event = None
                if value == "INDI":
                    current_indi = rest
                    current_fam = None
                    individuals[current_indi] = {
                        "name": "",
                        "givn": "",
                        "surn": "",
                        "sex": "",
                        "birth": "",
                        "death": "",
                        "famc": "",
                        "fams": [],
                    }
                elif value == "FAM":
                    current_fam = rest
                    current_indi = None
                    families[current_fam] = {"husb": "", "wife": "", "chil": []}
                else:
                    current_indi = None
                    current_fam = None
            elif level == 1:
                current_event = rest
                if current_indi:
                    if rest == "NAME":
                        individuals[current_indi]["name"] = value
                    elif rest == "SEX":
                        individuals[current_indi]["sex"] = value
                    elif rest == "FAMC":
                        individuals[current_indi]["famc"] = value
                    elif rest == "FAMS":
                        individuals[current_indi]["fams"].append(value)
                elif current_fam:
                    if rest == "HUSB":
                        families[current_fam]["husb"] = value
                    elif rest == "WIFE":
                        families[current_fam]["wife"] = value
                    elif rest == "CHIL":
                        families[current_fam]["chil"].append(value)
            elif level == 2 and current_indi:
                if rest == "GIVN":
                    individuals[current_indi]["givn"] = value
                elif rest == "SURN":
                    individuals[current_indi]["surn"] = value
                elif rest == "DATE":
                    if current_event == "BIRT":
                        individuals[current_indi]["birth"] = value
                    elif current_event == "DEAT":
                        individuals[current_indi]["death"] = value

    return individuals, families


def get_name(indi_id: str, individuals: dict) -> str:
    d = individuals.get(indi_id, {})
    name = d.get("name", "").replace("/", "").strip()
    if not name:
        name = f"{d.get('givn', '').strip()} {d.get('surn', '').strip()}".strip()
    return name or indi_id


def get_birth(indi_id: str, individuals: dict) -> str:
    birth = individuals.get(indi_id, {}).get("birth", "")
    if not birth:
        return "?"
    m = re.search(r"\b(\d{4})\b", birth)
    return m.group(1) if m else birth


def get_parents(indi_id: str, individuals: dict, families: dict):
    famc = individuals.get(indi_id, {}).get("famc", "")
    if not famc:
        return None, None
    fam = families.get(famc, {})
    return fam.get("husb"), fam.get("wife")


def find_individual(individuals: dict, pattern: str) -> str | None:
    """Find an individual whose cleaned name contains the search pattern."""
    pattern_lower = pattern.lower()
    for indi_id, data in individuals.items():
        name = get_name(indi_id, individuals).lower()
        if pattern_lower in name:
            return indi_id
    return None


def find_path_to_ancestor(
    start_id: str, target_id: str, individuals: dict, families: dict
) -> list[str] | None:
    """BFS upward from start to target, returning [start, ..., target]."""
    queue = deque([(start_id, [start_id])])
    seen = set()
    while queue:
        current, path = queue.popleft()
        if current == target_id:
            return path
        if current in seen:
            continue
        seen.add(current)
        dad, mum = get_parents(current, individuals, families)
        for p in (dad, mum):
            if p and p not in seen:
                queue.append((p, path + [p]))
    return None


def text_cell(cell_id: str, x: float, y: float, name: str, birth: str) -> str:
    return (
        f'        <mxCell id="{cell_id}" value="{name}&#xa;(b. {birth})" '
        f'style="text;html=1;strokeColor=none;fillColor=#ffffff;align=center;'
        f'verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=11;'
        f'fontFamily={FONT_FAMILY};fontColor={STROKE_COLOR};" vertex="1" parent="1">\n'
        f'          <mxGeometry x="{x}" y="{y}" width="{TEXT_W}" height="{TEXT_H}" as="geometry" />\n'
        f'        </mxCell>'
    )


def marriage_lines(mid: str, x1: float, x2: float, y: float) -> str:
    width = x2 - x1
    return (
        f'        <mxCell id="{mid}a" value="" style="shape=line;direction=east;'
        f'whiteSpace=wrap;html=1;strokeColor={STROKE_COLOR};strokeWidth=1.5;" vertex="1" parent="1">\n'
        f'          <mxGeometry x="{x1}" y="{y}" width="{width}" height="1" as="geometry" />\n'
        f'        </mxCell>\n'
        f'        <mxCell id="{mid}b" value="" style="shape=line;direction=east;'
        f'whiteSpace=wrap;html=1;strokeColor={STROKE_COLOR};strokeWidth=1.5;" vertex="1" parent="1">\n'
        f'          <mxGeometry x="{x1}" y="{y + MARRIAGE_LINE_GAP}" width="{width}" height="1" as="geometry" />\n'
        f'        </mxCell>'
    )


def vline(vid: str, x: float, y: float, h: float) -> str:
    return (
        f'        <mxCell id="{vid}" value="" style="shape=rect;whiteSpace=wrap;html=1;'
        f'fillColor={STROKE_COLOR};strokeColor=none;" vertex="1" parent="1">\n'
        f'          <mxGeometry x="{x - 1}" y="{y}" width="2" height="{h}" as="geometry" />\n'
        f'        </mxCell>'
    )


def generate_drawio(path_ids: list[str], individuals: dict, families: dict, title: str) -> str:
    # Build couple rows from the bottom (focus) up to the top (target).
    # Each row is (direct_ancestor_id, spouse_id, child_id).
    rows: list[tuple[str, str | None, str]] = []
    for i in range(len(path_ids) - 1):
        child_id = path_ids[i]
        direct_ancestor_id = path_ids[i + 1]
        dad, mum = get_parents(child_id, individuals, families)
        if dad == direct_ancestor_id:
            spouse_id = mum
        elif mum == direct_ancestor_id:
            spouse_id = dad
        else:
            # Should not happen for a direct path, but be defensive.
            spouse_id = None
        rows.append((direct_ancestor_id, spouse_id, child_id))

    # Layout constants
    couple_width = 2 * TEXT_W + MARRIAGE_GAP
    page_width = couple_width + 2 * MARGIN
    page_height = (len(rows) + 1) * GENERATION_HEIGHT + TEXT_H + 2 * MARGIN

    parts: list[str] = []
    parts.append(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="drawio" version="26.0.0">\n'
        '  <diagram name="Pedigree">\n'
        f'    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" '
        f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="{page_width}" pageHeight="{page_height}" math="0" shadow="0">\n'
        '      <root>\n'
        '        <mxCell id="0" />\n'
        '        <mxCell id="1" parent="0" />'
    )

    parts.append(
        f'\n        <!-- Title -->\n'
        f'        <mxCell id="title" value="{title}" style="text;html=1;strokeColor=none;'
        f'fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;'
        f'fontSize=14;fontFamily={FONT_FAMILY};fontStyle=1" vertex="1" parent="1">\n'
        f'          <mxGeometry x="{MARGIN}" y="{MARGIN / 2}" width="{couple_width}" '
        f'height="20" as="geometry" />\n'
        f'        </mxCell>'
    )

    # Start from the bottom; focus person's parents are row 0.
    centre_x = MARGIN + TEXT_W + MARRIAGE_GAP / 2
    top_y = MARGIN + 20.0 + len(rows) * GENERATION_HEIGHT

    # Compute y for each row; row 0 is the focus person's parents at the bottom.
    row_data: list[dict] = []
    for idx, (direct_id, spouse_id, child_id) in enumerate(rows):
        y = top_y - idx * GENERATION_HEIGHT
        direct_x = MARGIN
        spouse_x = MARGIN + TEXT_W + MARRIAGE_GAP
        marriage_y = y + MARRIAGE_Y_OFFSET
        row_data.append({
            "direct_id": direct_id,
            "spouse_id": spouse_id,
            "child_id": child_id,
            "direct_x": direct_x,
            "spouse_x": spouse_x,
            "y": y,
            "marriage_y": marriage_y,
            "marriage_x": centre_x,
        })

    # The focus person (path_ids[0]) sits one generation below their parents (row 0).
    focus_id = path_ids[0]
    focus_y = row_data[0]["y"] + GENERATION_HEIGHT
    focus_x = centre_x - TEXT_W / 2

    # Marriage lines first (under labels)
    parts.append("\n        <!-- Marriage lines -->")
    for idx, row in enumerate(row_data):
        if row["spouse_id"]:
            parts.append(
                marriage_lines(
                    f"m{idx}",
                    row["direct_x"] + TEXT_W,
                    row["spouse_x"],
                    row["marriage_y"],
                )
            )

    # Person labels
    parts.append("\n        <!-- Names -->")
    for idx, row in enumerate(row_data):
        direct_name = get_name(row["direct_id"], individuals)
        direct_birth = get_birth(row["direct_id"], individuals)
        parts.append(
            text_cell(f"p{idx}a", row["direct_x"], row["y"], direct_name, direct_birth)
        )
        if row["spouse_id"]:
            spouse_name = get_name(row["spouse_id"], individuals)
            spouse_birth = get_birth(row["spouse_id"], individuals)
            parts.append(
                text_cell(f"p{idx}b", row["spouse_x"], row["y"], spouse_name, spouse_birth)
            )

    # Focus person label at the bottom
    parts.append(
        text_cell(f"focus", focus_x, focus_y, get_name(focus_id, individuals), get_birth(focus_id, individuals))
    )

    # Descenders between generations
    parts.append("\n        <!-- Descent lines -->")
    for idx, row in enumerate(row_data):
        # Vertical line from this row's marriage line down to the child below.
        top_y_line = row["marriage_y"] + MARRIAGE_LINE_GAP + 1.0
        if idx == 0:
            # Child is the focus person (single label, no spouse).
            bottom_y = focus_y
        else:
            next_row = row_data[idx - 1]  # next row is physically below (idx decreases going down)
            bottom_y = next_row["marriage_y"]
        height = bottom_y - top_y_line
        parts.append(vline(f"v{idx}", row["marriage_x"], top_y_line, height))

    parts.append(
        '\n      </root>\n'
        '    </mxGraphModel>\n'
        '  </diagram>\n'
        '</mxfile>'
    )

    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Vertical direct-line pedigree from GEDCOM.")
    parser.add_argument("--gedcom", required=True, help="Path to GEDCOM file.")
    parser.add_argument("--from", dest="start", required=True, help='Focus person name, e.g. "Adam Short" or "@I123@".')
    parser.add_argument("--to", dest="target", required=True, help='Target ancestor name or ID, e.g. "Edward III Plantagenet" or "@I456@".')
    parser.add_argument("--output", required=True, help="Output draw.io XML path.")
    parser.add_argument("--title", default=None, help="Diagram title.")
    parser.add_argument("--font-family", default="Helvetica", help="Font family for labels and title (default Helvetica).")
    args = parser.parse_args()

    global FONT_FAMILY
    FONT_FAMILY = args.font_family

    individuals, families = parse_gedcom(args.gedcom)

    def resolve(ident: str) -> str | None:
        if ident.startswith("@I") and ident.endswith("@"):
            return ident if ident in individuals else None
        return find_individual(individuals, ident)

    start_id = resolve(args.start)
    if not start_id:
        print(f"Could not find focus person: {args.start}", file=sys.stderr)
        return 1
    target_id = resolve(args.target)
    if not target_id:
        print(f"Could not find target ancestor: {args.target}", file=sys.stderr)
        return 1

    path = find_path_to_ancestor(start_id, target_id, individuals, families)
    if not path:
        print(
            f"No ancestral path found between {get_name(start_id, individuals)} "
            f"and {get_name(target_id, individuals)}.",
            file=sys.stderr,
        )
        return 1

    print(f"Path length: {len(path)}")
    for i, pid in enumerate(path):
        print(f"  {i + 1}. {get_name(pid, individuals)} ({pid})")

    title = args.title or f"Pedigree: {get_name(target_id, individuals)} to {get_name(start_id, individuals)}"
    xml = generate_drawio(path, individuals, families, title)
    Path(args.output).write_text(xml, encoding="utf-8")
    print(f"Wrote {len(path)} generations to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
