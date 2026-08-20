#!/usr/bin/env python3
"""Generate a vertical direct-line pedigree chart from GEDCOM.

Shows only the ancestors on the path from a focus person up to a target
ancestor, plus each ancestor's spouse.  No siblings, aunts, uncles, or cousins.

This script shares its GEDCOM/lookup helpers (``parse_gedcom``, ``get_name``,
``get_parents``, ``find_individual_by_name``) and its cell-rendering helpers
(``text_cell``, ``hline``, ``vrect``, ``label_value``) with the other
generation scripts in this skill.  Layout tweaks made in ``drawio_layout.py``
(``DESCENDER_OFFSET``, ``CHILD_DROP``, ``INTER_GEN_GAP``, ``STROKE``,
``MARRIAGE_Y_OFFSET``, etc.) propagate here automatically.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import deque
from pathlib import Path

from drawio_layout import (
    FONT_COLOR,
    FONT_SIZE,
    MARRIAGE_GAP,
    MARRIAGE_LINE_GAP,
    MARRIAGE_Y_OFFSET,
    STROKE,
    TITLE_Y,
    couple_descender_top,
    hline,
    label_value,
    min_generation_height,
    text_cell,
    vrect,
)
from parse_gedcom import (
    find_individual_substring,
    get_name,
    get_parents,
    parse_gedcom,
)


# Pedigree-script-specific layout constants -----------------------------------
# The vertical pedigree has slightly wider labels than the shared default to
# accommodate "Name (b. Year)" on two lines, and a tighter page margin than
# the shared default.  All marriage-line and font constants come from the
# shared ``drawio_layout`` module so a tweak there flows through.
TEXT_W = 110.0
TEXT_H = 38.0
MARGIN = 20.0

# Per-generation vertical spacing.  Derived from ``min_generation_height``
# so any tweak to ``DESCENDER_OFFSET``/``CHILD_DROP``/``INTER_GEN_GAP`` in
# ``drawio_layout.py`` flows through here.  An 80 px floor keeps the
# pedigree compact (no sibling bar, no inter-generation padding).
_MIN_GENERATION_HEIGHT = min_generation_height(TEXT_H)
GENERATION_HEIGHT = max(80.0, _MIN_GENERATION_HEIGHT)


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


def get_birth(indi_id: str, individuals: dict) -> str:
    """Pedigree-specific helper: returns the 4-digit birth year, or '?' if missing.

    The shared ``parse_gedcom.get_birth`` returns the full GEDCOM date string;
    for the pedigree we want just the year so it fits on one line in the
    "Name (b. Year)" label format.
    """
    birth = individuals.get(indi_id, {}).get("birth", "")
    if not birth:
        return "?"
    m = re.search(r"\b(\d{4})\b", birth)
    return m.group(1) if m else birth


def marriage_pair_lines(mid: str, x1: float, x2: float, y: float) -> str:
    """Render the double horizontal marriage line for a couple.

    Two parallel ``shape=line`` cells stacked with ``MARRIAGE_LINE_GAP`` between
    them, starting at ``(x1, y)`` and ending at ``(x2, y)``.  Reuses the shared
    ``hline`` helper.
    """
    width = x2 - x1
    return "\n".join([
        hline("1", f"{mid}a", x1, y, width),
        hline("1", f"{mid}b", x1, y + MARRIAGE_LINE_GAP, width),
    ])


def descender_line(vid: str, x: float, y: float, h: float) -> str:
    """Vertical descender from parent marriage line down to child label.

    2 px wide, centred on ``x`` (so the shared ``vrect`` is placed at ``x - 1``).
    """
    return vrect("1", vid, x - 1.0, y, h, width=2.0)


def generate_drawio(path_ids: list[str], individuals: dict, families: dict, title: str, font_family: str) -> str:
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

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<mxfile host="drawio" version="26.0.0">',
        '  <diagram name="Pedigree">',
        f'    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" '
        f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="{page_width}" pageHeight="{page_height}" math="0" shadow="0">',
        '      <root>',
        '        <mxCell id="0" />',
        '        <mxCell id="1" parent="0" />',
        '',
        f'        <mxCell id="title" value="{title}" style="text;html=1;strokeColor=none;'
        f'fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;'
        f'fontSize=14;fontFamily={font_family};fontStyle=1" vertex="1" parent="1">',
        f'          <mxGeometry x="{MARGIN}" y="{MARGIN / 2}" width="{couple_width}" '
        f'height="20" as="geometry" />',
        '        </mxCell>',
    ]

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
    parts.append("")
    parts.append("        <!-- Marriage lines -->")
    for idx, row in enumerate(row_data):
        if row["spouse_id"]:
            parts.append(
                marriage_pair_lines(
                    f"m{idx}",
                    row["direct_x"] + TEXT_W,
                    row["spouse_x"],
                    row["marriage_y"],
                )
            )

    # Person labels
    parts.append("")
    parts.append("        <!-- Names -->")
    for idx, row in enumerate(row_data):
        parts.append(
            text_cell(
                "1",
                f"p{idx}a",
                row["direct_x"],
                row["y"],
                TEXT_W,
                TEXT_H,
                get_name(row["direct_id"], individuals),
                get_birth(row["direct_id"], individuals),
                font_family,
                font_size=FONT_SIZE,
                font_color=FONT_COLOR,
            )
        )
        if row["spouse_id"]:
            parts.append(
                text_cell(
                    "1",
                    f"p{idx}b",
                    row["spouse_x"],
                    row["y"],
                    TEXT_W,
                    TEXT_H,
                    get_name(row["spouse_id"], individuals),
                    get_birth(row["spouse_id"], individuals),
                    font_family,
                    font_size=FONT_SIZE,
                    font_color=FONT_COLOR,
                )
            )

    # Focus person label at the bottom
    parts.append("")
    parts.append(
        text_cell(
            "1",
            "focus",
            focus_x,
            focus_y,
            TEXT_W,
            TEXT_H,
            get_name(focus_id, individuals),
            get_birth(focus_id, individuals),
            font_family,
            font_size=FONT_SIZE,
            font_color=FONT_COLOR,
        )
    )

    # Descenders between generations.  Use the shared ``couple_descender_top``
    # helper so the marriage-line-bottom offset tracks the shared
    # ``MARRIAGE_Y_OFFSET`` and ``MARRIAGE_LINE_GAP`` constants.
    parts.append("")
    parts.append("        <!-- Descent lines -->")
    for idx, row in enumerate(row_data):
        # Vertical line from this row's marriage line down to the child below.
        # ``couple_descender_top`` returns the top of the descender for a
        # couple rooted at the given y; we apply it to the absolute y of the
        # marriage line centre (which is the same offset as the row's y).
        top_y_line = couple_descender_top(row["y"])
        if idx == 0:
            # Child is the focus person (single label, no spouse).
            bottom_y = focus_y
        else:
            next_row = row_data[idx - 1]
            bottom_y = next_row["marriage_y"]
        height = bottom_y - top_y_line
        parts.append(descender_line(f"v{idx}", row["marriage_x"], top_y_line, height))

    parts.append('      </root>')
    parts.append('    </mxGraphModel>')
    parts.append('  </diagram>')
    parts.append('</mxfile>')

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

    individuals, families = parse_gedcom(args.gedcom)

    def resolve(ident: str) -> str | None:
        if ident.startswith("@I") and ident.endswith("@"):
            return ident if ident in individuals else None
        return find_individual_substring(individuals, ident)

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
    xml = generate_drawio(path, individuals, families, title, args.font_family)
    Path(args.output).write_text(xml, encoding="utf-8")
    print(f"Wrote {len(path)} generations to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())