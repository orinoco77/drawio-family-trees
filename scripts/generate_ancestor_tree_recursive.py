#!/usr/bin/env python3
"""Generate a bottom-up recursive ancestor tree from GEDCOM.

Each node is a couple (the focus person + their spouse). The focus person's
parents are shown as a couple above the focus person; the spouse's parents are
shown as a couple above the spouse. Recurse upward.

Layout is bottom-up: subtree widths are computed first, then each couple is
placed so the two parent couples sit directly above the husband and wife.

This script shares its constants and GEDCOM/lookup helpers with the other
generation scripts in this skill (``parse_gedcom.py`` and ``drawio_layout.py``),
so layout tweaks made in those modules propagate here.  It does NOT have a
sibling-bar concept (the descender goes from parent marriage directly to child
label) so the bar-related constants ``DESCENDER_OFFSET``/``CHILD_DROP`` do not
apply; instead the per-generation spacing is controlled by ``GENERATION_HEIGHT``
below, which is computed from the shared ``min_generation_height`` helper so
the parent-to-child geometry stays in lockstep with the other charts.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from drawio_layout import (
    STROKE,
    TITLE_Y,
    min_generation_height,
)
from parse_gedcom import get_name, get_parents, get_spouses, parse_gedcom


# Ancestor-script-specific layout constants -----------------------------------
# These deliberately differ from the shared ``drawio_layout`` values to keep
# the ancestor chart's existing visual conventions:
#
#   * Wider labels (``TEXT_W = 110`` vs shared ``75``)
#   * Wider marriage gap (``MARRIAGE_GAP = 20`` vs shared ``14``)
#   * Marriage line drawn near the *bottom* of the parent text box
#     (``MARRIAGE_Y_OFFSET = TEXT_H - 10`` vs shared ``18`` = upper area)
#   * 4 px gap between the two marriage lines (vs shared ``3``)
#   * Tighter page margin (``MARGIN = 20`` vs shared ``40``)
#
# None of the shared module's geometry constants are imported here because
# the ancestor chart's visual conventions differ from the visitation chart;
# see ``references/layout-rules.md`` for the shared rule these constants
# implement in a different way.  All descender geometry is computed from
# these local constants in one place (``generate_drawio``) so future tweaks
# only need to happen there.
TEXT_W = 110.0
TEXT_H = 38.0
MIN_SPOUSE_GAP = 6.0
PAGE_CENTER_X = 850.0
MARGIN = 20.0
MARRIAGE_GAP = 20.0
MARRIAGE_Y_OFFSET = TEXT_H - 10.0
MARRIAGE_LINE_GAP = 4.0

# Per-generation vertical spacing.  Derived from ``min_generation_height``
# so any tweak to ``DESCENDER_OFFSET``/``CHILD_DROP``/``INTER_GEN_GAP`` in
# ``drawio_layout.py`` flows through here.  A 70 px floor keeps the ancestor
# chart compact (it has no sibling bar, so the shared minimum is too loose).
_MIN_GENERATION_HEIGHT = min_generation_height(TEXT_H)
GENERATION_HEIGHT = max(70.0, _MIN_GENERATION_HEIGHT)

# Page title height reserved above the chart.
TITLE_HEIGHT = TITLE_Y + 5.0

# Cell-rendering font family default; override with --font-family.
FONT_FAMILY_DEFAULT = "Helvetica"


def safe_id(indi_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", indi_id)


@dataclass
class Couple:
    husband_id: str | None
    wife_id: str | None
    blood_id: str | None = None
    father: Couple | None = None
    mother: Couple | None = None
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    center: float = 0.0
    left: float = 0.0
    right: float = 0.0
    husband_x: float = 0.0
    wife_x: float = 0.0
    origin: float = 0.0
    instance: int = 0


def build_tree(
    blood_id: str | None,
    spouse_id: str | None,
    max_depth: int,
    individuals: dict,
    families: dict,
    depth: int = 0,
    seen: set[tuple[str, ...]] | None = None,
    instance_counter: list[int] | None = None,
    recurse_spouse: bool = True,
) -> Couple | None:
    if blood_id is None and spouse_id is None:
        return None
    if instance_counter is None:
        instance_counter = [0]
    if seen is None:
        seen = set()

    key = tuple(sorted([x for x in (blood_id, spouse_id) if x]))
    if key in seen and depth > 0:
        instance_counter[0] += 1
        return Couple(husband_id=blood_id, wife_id=spouse_id, blood_id=blood_id or spouse_id, instance=instance_counter[0])
    seen.add(key)

    couple = Couple(husband_id=blood_id, wife_id=spouse_id, blood_id=blood_id or spouse_id, instance=instance_counter[0])
    instance_counter[0] += 1

    if depth >= max_depth:
        return couple

    if blood_id:
        dad, mum = get_parents(blood_id, individuals, families)
        if dad or mum:
            couple.father = build_tree(dad, mum, max_depth, individuals, families, depth + 1, seen, instance_counter)

    if recurse_spouse and spouse_id:
        dad, mum = get_parents(spouse_id, individuals, families)
        if dad or mum:
            couple.mother = build_tree(dad, mum, max_depth, individuals, families, depth + 1, seen, instance_counter)

    return couple


def compute_layout(couple: Couple | None) -> None:
    """Bottom-up width computation and top-down placement."""
    if couple is None:
        return

    # Recurse first
    compute_layout(couple.father)
    compute_layout(couple.mother)

    # Width of each parent's subtree
    father_width = couple.father.width if couple.father else TEXT_W
    mother_width = couple.mother.width if couple.mother else TEXT_W

    # We place father subtree on the left, mother subtree on the right, with a gap.
    # Husband is centred under father subtree; wife under mother subtree.
    # Husband/wife text boxes must not overlap and must have at least MARRIAGE_GAP.
    father_center = father_width / 2
    mother_center = father_width + MIN_SPOUSE_GAP + mother_width / 2

    husband_blood_center = father_center
    wife_blood_center = mother_center

    husband_x = husband_blood_center - TEXT_W / 2
    wife_x = wife_blood_center - TEXT_W / 2

    # Ensure marriage gap
    min_wife_x = husband_x + TEXT_W + MARRIAGE_GAP
    if wife_x < min_wife_x:
        shift = min_wife_x - wife_x
        wife_x += shift
        wife_blood_center += shift
        mother_center += shift
        # shift mother subtree origin
        # mother subtree origin was at father_width + MIN_SPOUSE_GAP; now it is wife_x + TEXT_W/2 - mother_width/2

    # Recompute mother subtree origin
    mother_origin = wife_blood_center - mother_width / 2

    # Couple bounding box
    couple.left = min(0.0, husband_x)
    couple.right = max(father_width + MIN_SPOUSE_GAP + mother_width, wife_x + TEXT_W)
    couple.width = couple.right - couple.left
    couple.center = (husband_blood_center + wife_blood_center) / 2
    couple.husband_x = husband_x
    couple.wife_x = wife_x

    # Store relative positions for subtrees
    if couple.father:
        couple.father.origin = 0.0
    if couple.mother:
        couple.mother.origin = mother_origin


def place_tree(couple: Couple, x: float, y: float) -> None:
    """Top-down placement: place this couple at (x, y) and recurse to parents."""
    if couple is None:
        return
    couple.x = x
    couple.y = y
    if couple.father:
        # father subtree origin is at 0 relative to couple; shift by couple.x - couple.left
        father_x = x - couple.left
        place_tree(couple.father, father_x, y - GENERATION_HEIGHT)
    if couple.mother:
        mother_x = x - couple.left + couple.mother.origin
        place_tree(couple.mother, mother_x, y - GENERATION_HEIGHT)


def collect_couples(couple: Couple | None, result: list[Couple] | None = None) -> list[Couple]:
    if result is None:
        result = []
    if couple is None:
        return result
    result.append(couple)
    collect_couples(couple.father, result)
    collect_couples(couple.mother, result)
    return result


def text_cell(cell_id: str, x: float, y: float, label: str, font_family: str) -> str:
    """Render a person label using the shared text_cell style.

    The shared helper produces a label with a white background; the original
    ancestor script used no background.  This wrapper passes ``label_value``
    directly and uses fillColor=none for visual parity with the previous
    output.
    """
    safe_label = html.escape(label).replace("\n", "&#xa;")
    return (
        f'    <mxCell id="{cell_id}" value="{safe_label}" '
        f'style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=12;fontFamily={html.escape(font_family)};" '
        f'vertex="1" parent="1">\n'
        f'      <mxGeometry x="{x:.1f}" y="{y:.1f}" width="{TEXT_W:.1f}" height="{TEXT_H:.1f}" as="geometry" />\n'
        f'    </mxCell>'
    )


def hline(cell_id: str, x: float, y: float, width: float) -> str:
    """Solid horizontal line, 2 px tall, using the shared stroke colour."""
    return (
        f'    <mxCell id="{cell_id}" value="" '
        f'style="shape=rect;whiteSpace=wrap;html=1;fillColor={STROKE};strokeColor=none;" '
        f'vertex="1" parent="1">\n'
        f'      <mxGeometry x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="2" as="geometry" />\n'
        f'    </mxCell>'
    )


def vline(cell_id: str, x: float, y: float, height: float) -> str:
    """Solid vertical line, 2 px wide, using the shared stroke colour."""
    return (
        f'    <mxCell id="{cell_id}" value="" '
        f'style="shape=rect;whiteSpace=wrap;html=1;fillColor={STROKE};strokeColor=none;" '
        f'vertex="1" parent="1">\n'
        f'      <mxGeometry x="{x:.1f}" y="{y:.1f}" width="2" height="{height:.1f}" as="geometry" />\n'
        f'    </mxCell>'
    )


def generate_drawio(root: Couple, title: str, font_family: str) -> str:
    couples = collect_couples(root)

    # Auto-fit: shift so top-left is at MARGIN (below title space)
    min_x = min(c.x + c.left for c in couples)
    max_x = max(c.x + c.right for c in couples)
    min_y = min(c.y for c in couples)
    max_y = max(c.y + TEXT_H for c in couples)

    dx = MARGIN - min_x
    dy = MARGIN + TITLE_HEIGHT - min_y

    for c in couples:
        c.x += dx
        c.y += dy

    page_width = max(max_x - min_x + 2 * MARGIN, 100)
    page_height = max(max_y - min_y + 2 * MARGIN + TITLE_HEIGHT, 100)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<mxfile host="app.diagrams.net" modified="2024-01-01T00:00:00.000Z" agent="generate_ancestor_tree_recursive.py" version="22.1.0" etag="none" type="device">',
        '  <diagram name="Page-1" id="page1">',
        '    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="' + str(int(page_width)) + '" pageHeight="' + str(int(page_height)) + '" background="#ffffff" math="0" shadow="0">',
        '      <root>',
        '        <mxCell id="0" />',
        '        <mxCell id="1" parent="0" />',
    ]

    # Title
    parts.append(
        f'    <mxCell id="title" value="{html.escape(title)}" '
        f'style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=14;fontFamily={html.escape(font_family)};fontStyle=1" '
        f'vertex="1" parent="1">\n'
        f'      <mxGeometry x="{MARGIN:.1f}" y="5" width="{page_width - 2 * MARGIN:.1f}" height="20" as="geometry" />\n'
        f'    </mxCell>'
    )

    cell_idx = 0
    drawn_h: set[tuple[float, float, float]] = set()
    drawn_v: set[tuple[float, float, float]] = set()

    for c in couples:
        # Husband label
        if c.husband_id:
            cell_idx += 1
            parts.append(
                text_cell(f"h{safe_id(c.husband_id)}_{c.instance}", c.x + c.husband_x, c.y, get_name(c.husband_id, individuals), font_family)
            )
        # Wife label
        if c.wife_id:
            cell_idx += 1
            parts.append(
                text_cell(f"w{safe_id(c.wife_id)}_{c.instance}", c.x + c.wife_x, c.y, get_name(c.wife_id, individuals), font_family)
            )

        # Double marriage line near bottom of text box
        if c.husband_id and c.wife_id:
            left = c.x + c.husband_x + TEXT_W
            right = c.x + c.wife_x
            width = right - left
            if width > 0.5:
                my = c.y + MARRIAGE_Y_OFFSET
                cell_idx += 1
                parts.append(hline(f"m{cell_idx}a", left, my, width))
                cell_idx += 1
                parts.append(hline(f"m{cell_idx}b", left, my + MARRIAGE_LINE_GAP, width))

    # Draw vertical descenders from each parent couple's marriage line down to child.
    # The marriage line is drawn as a 2 px-thick double line (top at y +
    # MARRIAGE_Y_OFFSET, bottom at y + MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP).
    # The descender starts ``LINE_THICKNESS + DESCENDER_CLEARANCE`` below the
    # lower marriage line and ends ``CHILD_CLEARANCE`` above the child's text
    # box.  These constants are the ancestor-script-specific equivalent of the
    # shared ``DESCENDER_OFFSET``/``CHILD_DROP`` constants.
    LINE_THICKNESS = 2.0
    DESCENDER_CLEARANCE = 1.0
    CHILD_CLEARANCE = 1.0
    for c in couples:
        if not (c.father or c.mother):
            continue
        child_marriage_x = c.x + c.center
        child_top = c.y

        for parent in (c.father, c.mother):
            if parent is None:
                continue
            parent_marriage_x = parent.x + parent.center
            # Top of the descender: just below the lower marriage line.
            top = parent.y + MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + LINE_THICKNESS + DESCENDER_CLEARANCE
            # End just above the child's text box
            bottom = child_top - CHILD_CLEARANCE
            height = bottom - top
            if height > 0:
                vkey = (round(parent_marriage_x, 1), round(top, 1), round(height, 1))
                if vkey not in drawn_v:
                    drawn_v.add(vkey)
                    cell_idx += 1
                    parts.append(vline(f"v{cell_idx}", parent_marriage_x, top, height))

    parts.extend([
        '      </root>',
        '    </mxGraphModel>',
        '  </diagram>',
        '</mxfile>',
    ])

    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a recursive bottom-up ancestor tree")
    parser.add_argument("--gedcom", required=True, help="Path to GEDCOM file")
    parser.add_argument("--root-id", required=True, help="Focus person ID")
    parser.add_argument("--generations", type=int, default=5, help="Number of ancestor generations")
    parser.add_argument("--output", required=True, help="Output drawio file")
    parser.add_argument("--title", help="Chart title")
    parser.add_argument("--font-family", default=FONT_FAMILY_DEFAULT, help="Font family for labels and title (default Helvetica).")
    args = parser.parse_args()

    global individuals, families
    individuals, families = parse_gedcom(args.gedcom)

    focus_id = args.root_id
    spouses = get_spouses(focus_id, individuals, families)
    spouse_id = spouses[0] if spouses else None

    root = build_tree(focus_id, spouse_id, args.generations, individuals, families, recurse_spouse=False)
    if root is None:
        print(f"Could not build tree for {focus_id}")
        sys.exit(1)

    compute_layout(root)

    # Center root on page
    place_tree(root, PAGE_CENTER_X - root.center + root.left, 300.0)

    title = args.title or f"Ancestors of {get_name(focus_id, individuals)}"
    xml = generate_drawio(root, title, args.font_family)

    Path(args.output).write_text(xml, encoding="utf-8")
    print(f"Root: {get_name(focus_id, individuals)} ({focus_id})")
    print(f"Wrote {len(collect_couples(root))} couples to {args.output}")


if __name__ == "__main__":
    main()