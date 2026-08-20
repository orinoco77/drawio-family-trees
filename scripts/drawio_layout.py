"""
Shared layout constants and helpers for drawio-family-trees generators.

The rules here are intended to be used by every chart generator so that all
family-tree diagrams share a single set of spacing and descender conventions.
"""

from __future__ import annotations

import html
import math
from typing import Iterable

# ---------------------------------------------------------------------------
# Core layout constants
# ---------------------------------------------------------------------------
TEXT_W = 75.0
DEFAULT_TEXT_H = 30.0
DEFAULT_TEXT_H_SMALL = 28.0
MARRIAGE_GAP = 14.0
MARRIAGE_Y_OFFSET = 18.0
MARRIAGE_LINE_GAP = 3.0
SIBLING_GAP = 12.0
DEFAULT_GENERATION_HEIGHT = 105.0
TITLE_Y = 20.0
MARGIN = 40.0
STROKE = "#333333"
FONT_SIZE = 11
FONT_COLOR = "#333333"

# Distance from the horizontal sibling bar down to the top of a child label.
CHILD_DROP = 12.0

# Vertical offset from parent label bottom to the sibling bar, in px.
# The visible "parent descender" length is roughly
# (max_label_h + DESCENDER_OFFSET) - (MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1).
DESCENDER_OFFSET = -8.0

# Extra vertical padding between an ancestor generation and its descendant generation,
# on top of (MARRIAGE_* + DESCENDER_OFFSET + CHILD_DROP).  Zero by default so the
# parent-driven sibling-bar position and the child-driven bar cap coincide exactly,
# making the parent-to-bar gap equal to DESCENDER_OFFSET (= -8 currently).
INTER_GEN_GAP = 0.0


def min_generation_height(max_label_h: float = DEFAULT_TEXT_H) -> float:
    """Minimum generation-to-generation y delta that lets the parent descender
    fit without the child-driven bar cap taking over.

    For a couple: descender_top is at (parent_root_y + MARRIAGE_Y_OFFSET +
    MARRIAGE_LINE_GAP + 1), the parent-driven sibling bar target is at
    descender_top + max_label_h + DESCENDER_OFFSET, and the lowest the
    child label can sit while still leaving CHILD_DROP above it is at
    target + CHILD_DROP.  Plus INTER_GEN_GAP for breathing room.
    """
    return (
        MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1.0
        + max_label_h + DESCENDER_OFFSET + CHILD_DROP + INTER_GEN_GAP
    )


# ---------------------------------------------------------------------------
# Marriage-pair selection for multi-spouse units
# ---------------------------------------------------------------------------
# A unit with multiple spouses stores them in the linear chain
# [S1, Blood, S2, S3, ...] where Blood is the unit's primary person and
# spouse_idx indexes the marriage:
#   - spouse_idx == 0 (or out of range): single-parent case (Blood only)
#   - spouse_idx == 1: marriage between S1 and Blood
#   - spouse_idx == 2: marriage between Blood and S2
#   - spouse_idx >= 3: marriage between (spouse_idx-1) and spouse_idx
# This module-level helper returns the (left, right) people that form a
# given marriage, so both generation scripts can render the marriage line
# the same way.
#
# NB: We don't take a dependency on the unit's `people` attribute type here
# because callers pass `unit.people` directly.  Keep the helper minimal.

def marriage_pair_people(unit_people: list, spouse_idx: int) -> tuple:
    """Return (left_person, right_person) for the marriage at spouse_idx.

    unit_people is a list of person objects, ordered as
    [S1, Blood, S2, S3, ...].  For a single parent (spouse_idx == 0 or
    out of range) returns (Blood, Blood) as a degenerate pair.

    Step-parents (people whose ``is_step_parent`` attribute is True) are
    spouses of the blood person's primary spouse (people[1]), so their
    marriage pair is (people[1], people[spouse_idx]).
    """
    if spouse_idx == 0 or spouse_idx >= len(unit_people):
        return unit_people[0], unit_people[0]
    # Step-parent: marriage is with people[1], not the blood person.
    if getattr(unit_people[spouse_idx], "is_step_parent", False):
        return unit_people[1], unit_people[spouse_idx]
    if len(unit_people) == 2:
        return unit_people[0], unit_people[1]
    if spouse_idx == 1:
        return unit_people[1], unit_people[0]  # S1, Blood
    if spouse_idx == 2:
        return unit_people[0], unit_people[2]  # Blood, S2
    return unit_people[spouse_idx - 1], unit_people[spouse_idx]


def marriage_pair_center(unit_people: list, spouse_idx: int, text_w: float) -> float:
    """Return the x-centre of the marriage between the two people at spouse_idx."""
    left, right = marriage_pair_people(unit_people, spouse_idx)
    return (left.x + text_w + right.x) / 2


# ---------------------------------------------------------------------------
# Label height estimation
# ---------------------------------------------------------------------------
def estimate_label_height(name: str, birth: str, width: float = TEXT_W) -> float:
    """Estimate the height of a label in px based on text wrapping."""
    chars_per_line = 14
    name_lines = (len(name) + chars_per_line - 1) // chars_per_line
    total_lines = max(1, name_lines) + 1
    return total_lines * 15.0


def compute_max_label_height(get_name, get_birth, indi_ids: Iterable[str]) -> float:
    """Return the tallest estimated label height for the given individuals."""
    heights = [
        estimate_label_height(get_name(iid), get_birth(iid))
        for iid in indi_ids
    ]
    return max(heights) if heights else DEFAULT_TEXT_H


# ---------------------------------------------------------------------------
# Vertical geometry helpers
#
# Rule: child labels are positioned relative to the sibling bar, not the parent
# labels.  Raising/lowering the sibling bar raises/lowers the child labels with
# it, keeping the sibling-bar-to-child-name drop constant.
# ---------------------------------------------------------------------------
def couple_descender_top(root_y: float) -> float:
    """Top of the vertical descender for a married couple.

    The descender starts just below the lower marriage line.
    """
    return root_y + MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1.0


def single_descender_top(root_y: float, max_label_h: float) -> float:
    """Top of the vertical descender for a single parent.

    The descender starts just below the label so it never cuts through text.
    """
    return root_y + max_label_h


def connector_y_from_parent(
    descender_top: float,
    max_label_h: float,
    descender_offset: float = DESCENDER_OFFSET,
) -> float:
    """Sibling-bar y when computing top-down from the parent generation.

    Targets a parent-to-sibling-bar drop of max_label_h + descender_offset.
    """
    return descender_top + max_label_h + descender_offset


def connector_y_from_child(
    child_y: float,
    child_drop: float = CHILD_DROP,
) -> float:
    """Sibling-bar y when computing bottom-up from the child generation."""
    return child_y - child_drop


def child_y_from_connector(
    connector_y: float,
    child_drop: float = CHILD_DROP,
) -> float:
    """Child-label y given the sibling-bar y."""
    return connector_y + child_drop


def resolve_connector_y(
    *,
    descender_top: float,
    max_label_h: float,
    child_y: float,
    descender_offset: float = DESCENDER_OFFSET,
    child_drop: float = CHILD_DROP,
) -> float:
    """Return the sibling-bar y for one parent group.

    Rule: child labels are positioned relative to the sibling bar (not the parent
    labels).  The bar is placed at the lower of two targets:

    1. The parent-driven position: ``descender_top + max_label_h + descender_offset``,
       which gives a comfortable parent-to-bar drop.
    2. The child-driven cap: ``child_y - child_drop``, which keeps the bar-to-child
       drop at exactly ``child_drop``.

    Whatever the layout chooses, the child-name drop stays at ``child_drop`` and
    the parent-to-bar drop absorbs the rest.
    """
    parent_target = descender_top + max_label_h + descender_offset
    child_cap = child_y - child_drop
    return max(parent_target, child_cap)


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------
def label_value(name: str, birth: str) -> str:
    birth = birth or ""
    name = html.escape(name)
    if birth:
        return f"{name}&#xa;(b. {html.escape(birth)})"
    return name


def text_cell(
    parent: str,
    cid: str,
    x: float,
    y: float,
    w: float,
    h: float,
    name: str,
    birth: str,
    font_family: str,
    font_size: int = FONT_SIZE,
    font_color: str = FONT_COLOR,
) -> str:
    val = label_value(name, birth)
    bg = (
        f'<mxCell id="{cid}_bg" value="" style="shape=rect;whiteSpace=wrap;html=1;'
        f'fillColor=#ffffff;strokeColor=none;" vertex="1" parent="{parent}">\n'
        f'  <mxGeometry x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" as="geometry"/>\n'
        f'</mxCell>'
    )
    txt = (
        f'<mxCell id="{cid}" value="{val}" style="text;html=1;strokeColor=none;'
        f'fillColor=#ffffff;align=center;verticalAlign=top;whiteSpace=wrap;rounded=0;'
        f'fontSize={font_size};fontColor={font_color};fontFamily={html.escape(font_family)};" '
        f'vertex="1" parent="{parent}">\n'
        f'  <mxGeometry x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" as="geometry"/>\n'
        f'</mxCell>'
    )
    return bg + "\n" + txt


def hline(parent: str, cid: str, x: float, y: float, width: float) -> str:
    return (
        f'<mxCell id="{cid}" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;'
        f'strokeColor={STROKE};strokeWidth=1.5;" vertex="1" parent="{parent}">\n'
        f'  <mxGeometry x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="1" as="geometry"/>\n'
        f'</mxCell>'
    )


def vrect(
    parent: str,
    cid: str,
    x: float,
    y: float,
    height: float,
    width: float = 2.0,
) -> str:
    return (
        f'<mxCell id="{cid}" value="" style="shape=rect;whiteSpace=wrap;html=1;'
        f'fillColor={STROKE};strokeColor=none;" vertex="1" parent="{parent}">\n'
        f'  <mxGeometry x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" as="geometry"/>\n'
        f'</mxCell>'
    )
