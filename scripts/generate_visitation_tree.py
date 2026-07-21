#!/usr/bin/env python3
"""
Generate a no-box, visitation-style family tree in draw.io XML from a GEDCOM file.

Layout strategy (hourglass, root in the middle generation):
- Collect `generations` levels of ancestors above the root and the same below.
- Render each person as a plain centred text label (no boxes).
- Draw orthogonal connectors: horizontal marriage line -> vertical descender ->
  horizontal child connector -> vertical lines to each child.
- Stop child-drop lines at the top edge of each name label.

Usage:
    python3 generate_visitation_tree.py --gedcom path/to/tree.ged \
        --root "Brian Stanley Short" --generations 2 --output tree.drawio
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Minimal GEDCOM parser
# ---------------------------------------------------------------------------


def parse_gedcom(path: str):
    individuals: dict[str, dict] = {}
    families: dict[str, dict] = {}

    current_indi: str | None = None
    current_fam: str | None = None
    current_event: str | None = None

    with open(path, "r", encoding="utf-8") as f:
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
                        # Keep the first NAME record; later ones are alternate names.
                        if not individuals[current_indi]["name"]:
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
    return individuals.get(indi_id, {}).get("birth", "")

def estimate_label_height(name: str, birth: str, width: float = 75.0) -> float:
    """Estimate the height of a label in px based on text wrapping."""
    chars_per_line = 14 
    name_lines = (len(name) + chars_per_line - 1) // chars_per_line
    total_lines = max(1, name_lines) + 1
    return total_lines * 15.0


def get_parents(indi_id: str, individuals: dict, families: dict):
    famc = individuals.get(indi_id, {}).get("famc", "")
    if not famc:
        return None, None
    fam = families.get(famc, {})
    return fam.get("husb"), fam.get("wife")


def get_children(indi_id: str, individuals: dict, families: dict):
    children = []
    for fams_id in individuals.get(indi_id, {}).get("fams", []):
        children.extend(families.get(fams_id, {}).get("chil", []))
    return children


def get_spouses(indi_id: str, individuals: dict, families: dict):
    spouses = []
    for fams_id in individuals.get(indi_id, {}).get("fams", []):
        fam = families.get(fams_id, {})
        if fam.get("husb") == indi_id:
            spouses.append(fam.get("wife"))
        elif fam.get("wife") == indi_id:
            spouses.append(fam.get("husb"))
    return [s for s in spouses if s]


def find_individual_by_name(individuals: dict, given: str, surname: str) -> str | None:
    for indi_id, data in individuals.items():
        if data.get("surn") == surname and given in data.get("givn", ""):
            return indi_id
    return None


# ---------------------------------------------------------------------------
# Layout engine
# ---------------------------------------------------------------------------


@dataclass
class Person:
    indi_id: str
    name: str
    birth: str
    x: float = 0.0
    is_spouse: bool = False


@dataclass
class FamilyUnit:
    """A person (people[0]) plus zero or more spouses, plus their children."""

    people: list[Person]
    children: list[FamilyUnit] = field(default_factory=list)
    # children grouped by spouse index (0 = children with no spouse, 1+ = spouse at people[index])
    spouse_children: list[list[FamilyUnit]] = field(default_factory=list)
    generation: int = 0
    x: float = 0.0
    y: float = 0.0
    width: float = 120.0
    center: float = 0.0
    # For ancestor links in mixed charts: maps child unit id -> x-centre of the
    # specific child person that connects to this parent unit.
    child_centers: dict[int, float] = field(default_factory=dict)

    @property
    def is_couple(self) -> bool:
        return len(self.people) >= 2

    @property
    def left_x(self) -> float:
        return self.center - self.width / 2

    @property
    def right_x(self) -> float:
        return self.center + self.width / 2

    def spouse_index(self, spouse_id: str | None) -> int:
        if not spouse_id:
            return 0
        for i, p in enumerate(self.people[1:], start=1):
            if p.indi_id == spouse_id:
                return i
        return 0


TEXT_W = 75.0
DEFAULT_TEXT_H = 30.0
DEFAULT_TEXT_H_SMALL = 28.0
DEFAULT_GENERATION_HEIGHT = 105.0
MARRIAGE_GAP = 14.0
MIN_SIBLING_GAP = 12.0
MARRIAGE_Y_OFFSET = 18.0
MARRIAGE_LINE_GAP = 3.0
CHILD_CONNECTOR_STAGGER = 4.0  # vertical offset between child connectors of different spouses
STROKE_COLOR = "#333333"
FONT_FAMILY = "Helvetica"  # default font; override with --font-family

# Unicode superscript digits for duplicate-person markers
SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"

# Dynamic heights calculated during runtime
MAX_LABEL_H = DEFAULT_TEXT_H
MAX_LABEL_H_SMALL = DEFAULT_TEXT_H_SMALL
CURRENT_GEN_H = DEFAULT_GENERATION_HEIGHT
DESCENDER_LENGTH = DEFAULT_TEXT_H + 20.0


def make_unit(root_id: str | None, spouse_ids: list[str], individuals: dict, generation: int) -> FamilyUnit:
    people: list[Person] = []
    if root_id:
        people.append(Person(root_id, get_name(root_id, individuals), get_birth(root_id, individuals), is_spouse=False))
    for spouse_id in spouse_ids:
        people.append(
            Person(spouse_id, get_name(spouse_id, individuals), get_birth(spouse_id, individuals), is_spouse=True)
        )
    width = _unit_width(len(people) - 1)
    return FamilyUnit(people=people, generation=generation, width=width, spouse_children=[[] for _ in range(len(people))])


def build_ancestors(root_id: str, generations: int, individuals: dict, families: dict) -> list[list[FamilyUnit]]:
    """Return ancestor generations as a list. Index 0 = parents of root."""
    result: list[list[FamilyUnit]] = []
    current_ids = [root_id]

    for gen in range(1, generations + 1):
        next_ids: list[str] = []
        gen_units: list[FamilyUnit] = []
        seen: set[tuple[str, ...]] = set()
        for indi_id in current_ids:
            dad, mum = get_parents(indi_id, individuals, families)
            key = tuple(sorted([x for x in (dad, mum) if x]))
            if not key or key in seen:
                continue
            seen.add(key)
            unit = make_unit(dad, [mum] if mum else [], individuals, generation=-gen)
            gen_units.append(unit)
            if dad:
                next_ids.append(dad)
            if mum:
                next_ids.append(mum)
        if not gen_units:
            break
        result.append(gen_units)
        current_ids = next_ids

    return result


def build_descendants(
    root_unit: FamilyUnit, generations: int, individuals: dict, families: dict
) -> list[list[FamilyUnit]]:
    """Populate root_unit.spouse_children and return descendant generations.

    Index 0 of the returned list = children of root.
    """
    result: list[list[FamilyUnit]] = []
    current_units: list[FamilyUnit] = [root_unit]

    for gen in range(1, generations + 1):
        next_units: list[FamilyUnit] = []
        seen_child_ids: set[str] = set()

        for parent_unit in current_units:
            indi_id = parent_unit.people[0].indi_id
            for fams_id in individuals.get(indi_id, {}).get("fams", []):
                fam = families.get(fams_id, {})
                if fam.get("husb") == indi_id:
                    spouse_id = fam.get("wife")
                elif fam.get("wife") == indi_id:
                    spouse_id = fam.get("husb")
                else:
                    continue
                spouse_idx = parent_unit.spouse_index(spouse_id)
                for child_id in fam.get("chil", []):
                    if child_id in seen_child_ids:
                        continue
                    seen_child_ids.add(child_id)
                    child_spouses = get_spouses(child_id, individuals, families)
                    child_unit = make_unit(child_id, child_spouses, individuals, generation=gen)
                    parent_unit.spouse_children[spouse_idx].append(child_unit)
                    next_units.append(child_unit)

        # Reorder spouses so smaller child groups sit on the far left (S1),
        # larger groups extend to the right.
        for parent_unit in current_units:
            _sort_spouses_by_child_count(parent_unit, individuals, families)
            # Width may have changed if spouses were reordered; recompute
            _recompute_unit_geometry(parent_unit)

        if not next_units:
            break
        result.append(next_units)
        current_units = next_units

    return result


def _sort_spouses_by_child_count(unit: FamilyUnit, individuals: dict, families: dict) -> None:
    """Reorder spouses so smaller child groups sit on the far left (S1),
    larger groups extend to the right. Blood person is at index 1.
    """
    if len(unit.people) <= 2:
        return  # 0 or 1 spouse: nothing to reorder

    # Map each spouse ID to number of children in this tree
    counts: dict[str, int] = {}
    for spouse_idx, group in enumerate(unit.spouse_children):
        if spouse_idx == 0:
            continue  # no-spouse group
        spouse_id = unit.people[spouse_idx].indi_id
        counts[spouse_id] = len(group)

    # Keep people[0]; sort spouses by child count ascending, then by birth year ascending
    spouses = unit.people[1:]

    def sort_key(person: Person) -> tuple:
        birth_year = _birth_year(person.birth)
        return (counts.get(person.indi_id, 0), birth_year if birth_year is not None else 9999)

    sorted_spouses = sorted(spouses, key=sort_key)

    # Reorder people
    unit.people = [unit.people[0]] + sorted_spouses

    # Reorder spouse_children to match
    old_groups = unit.spouse_children[1:]
    new_groups: list[list[FamilyUnit]] = []
    for i, spouse in enumerate(sorted_spouses):
        # Find this spouse's old group index (it was at i+1 in old order)
        old_idx = next(j for j, p in enumerate(spouses) if p.indi_id == spouse.indi_id)
        new_groups.append(old_groups[old_idx])
    unit.spouse_children = [unit.spouse_children[0]] + new_groups


def collect_siblings(root_id: str, individuals: dict, families: dict) -> list[str]:
    famc = individuals.get(root_id, {}).get("famc", "")
    if not famc:
        return []
    return [c for c in families.get(famc, {}).get("chil", []) if c != root_id]


def _birth_year(birth: str) -> int | None:
    """Extract a 4-digit year from a birth string, or None."""
    if not birth:
        return None
    m = re.search(r"\b(\d{4})\b", birth)
    return int(m.group(1)) if m else None


def blood_center(unit: FamilyUnit) -> float:
    """Return the x-centre of the blood-relative person (people[0]) in the unit."""
    return unit.people[0].x + TEXT_W / 2


def _recompute_unit_geometry(unit: FamilyUnit) -> None:
    left = min(p.x for p in unit.people)
    right = max(p.x + TEXT_W for p in unit.people)
    unit.width = right - left
    unit.center = (left + right) / 2


def _shift_unit(unit: FamilyUnit, delta: float) -> None:
    for p in unit.people:
        p.x += delta
    unit.center += delta


def _unit_width(num_spouses: int) -> float:
    """Width of a unit with the blood person and num_spouses spouses in a linear chain."""
    if num_spouses <= 0:
        return TEXT_W
    # One spouse: [Blood, Spouse] -> 2 people, 1 gap.
    # N>=2 spouses: [S1, Blood, S2, ..., SN] -> N+1 people, N gaps.
    return (num_spouses + 1) * TEXT_W + max(num_spouses, 1) * MARRIAGE_GAP


def _apply_unit_x(unit: FamilyUnit) -> None:
    """Position people in a linear chain around unit.center.

    - 0 spouses: blood person centred.
    - 1 spouse: [Blood, Spouse].
    - N>=2 spouses: [Spouse1, Blood, Spouse2, ..., SpouseN].
    """
    num_spouses = len(unit.people) - 1
    if num_spouses <= 0:
        unit.people[0].x = unit.center - TEXT_W / 2
        return

    width = _unit_width(num_spouses)
    left = unit.center - width / 2
    step = TEXT_W + MARRIAGE_GAP
    if num_spouses == 1:
        unit.people[0].x = left                   # Blood
        unit.people[1].x = left + step            # Spouse
    else:
        # [S1, Blood, S2, S3, ...]
        s1_x = left
        blood_x = left + step
        unit.people[0].x = blood_x                # Blood
        unit.people[1].x = s1_x                   # S1
        for i in range(2, len(unit.people)):
            unit.people[i].x = blood_x + (i - 1) * step  # S2, S3, ...
    _recompute_unit_geometry(unit)


def place_unit_at_blood_center(unit: FamilyUnit, center_x: float, y: float) -> None:
    """Place unit so the blood-relative person's centre is at center_x."""
    unit.y = y
    num_spouses = len(unit.people) - 1
    step = TEXT_W + MARRIAGE_GAP
    if num_spouses <= 0:
        unit.people[0].x = center_x - TEXT_W / 2
    elif num_spouses == 1:
        unit.people[0].x = center_x - TEXT_W / 2
        unit.people[1].x = center_x + TEXT_W / 2 + MARRIAGE_GAP
    else:
        # [S1, Blood, S2, ..., SN]
        unit.people[0].x = center_x - TEXT_W / 2                       # Blood
        unit.people[1].x = center_x - TEXT_W / 2 - MARRIAGE_GAP - TEXT_W  # S1
        for i in range(2, len(unit.people)):
            unit.people[i].x = center_x + TEXT_W / 2 + MARRIAGE_GAP + (i - 2) * step  # S2, S3, ...
    _recompute_unit_geometry(unit)


def layout_children(parent_center: float, children: list[FamilyUnit], y: float) -> None:
    """Place child units so their blood children are centred under parent_center."""
    if not children:
        return

    n = len(children)
    total_width = n * TEXT_W + MIN_SIBLING_GAP * (n - 1)
    left = parent_center - total_width / 2

    for child in children:
        place_unit_at_blood_center(child, left + TEXT_W / 2, y)
        left += TEXT_W + MIN_SIBLING_GAP

    # Resolve overlaps: a spouse may extend into the next child's territory
    for _ in range(20):
        moved = False
        for i in range(n - 1):
            left_child = children[i]
            right_child = children[i + 1]
            overlap = left_child.right_x + MIN_SIBLING_GAP - right_child.left_x
            if overlap > 0:
                for j in range(i + 1, n):
                    _shift_unit(children[j], overlap + 1)
                moved = True
        if not moved:
            break

    # Recenter the blood children on the parent centre
    blood_centers = [blood_center(c) for c in children]
    group_center = (min(blood_centers) + max(blood_centers)) / 2
    delta = parent_center - group_center
    for child in children:
        _shift_unit(child, delta)


# ---------------------------------------------------------------------------
# Overlap resolution
# ---------------------------------------------------------------------------


def _resolve_overlaps(units: list[FamilyUnit], target_center: float, recenter: bool = True) -> None:
    """Push apart overlapping units. Only recenter the group if recenter=True."""
    if len(units) < 2:
        if recenter and units:
            delta = target_center - units[0].center
            units[0].center += delta
            _apply_unit_x(units[0])
        return

    sorted_units = sorted(units, key=lambda u: u.center)
    for _ in range(40):
        moved = False
        for i in range(len(sorted_units) - 1):
            left = sorted_units[i]
            right = sorted_units[i + 1]
            overlap = left.right_x + MIN_SIBLING_GAP - right.left_x
            if overlap > 0:
                # Shift the right unit(s) by the full overlap so gaps only grow.
                for j in range(i + 1, len(sorted_units)):
                    sorted_units[j].center += overlap + 0.01
                    _apply_unit_x(sorted_units[j])
                moved = True
        if not moved:
            break

    if recenter:
        group_center = (sorted_units[0].center + sorted_units[-1].center) / 2
        delta = target_center - group_center
        for unit in sorted_units:
            unit.center += delta
            _apply_unit_x(unit)


@dataclass
class Extent:
    """Bounding extent of a laid-out subtree."""

    left: float
    right: float
    center: float
    unit: FamilyUnit | None = None
    children: list[Extent] = field(default_factory=list)

    def shift(self, dx: float) -> None:
        self.left += dx
        self.right += dx
        self.center += dx
        for child in self.children:
            child.shift(dx)
        if self.unit:
            for p in self.unit.people:
                p.x += dx
            _recompute_unit_geometry(self.unit)


def _combine_extents(extents: list[Extent], gap: float) -> None:
    """Place extents left-to-right with the given gap, shifting each in place."""
    x = 0.0
    for extent in extents:
        extent.shift(x - extent.left)
        x = extent.right + gap


def _marriage_offsets(num_spouses: int) -> list[float]:
    """Offsets from the blood person's centre to each marriage midpoint."""
    if num_spouses <= 0:
        return []
    step = TEXT_W + MARRIAGE_GAP
    if num_spouses == 1:
        # [Blood, Spouse]
        return [step / 2]
    # [S1, Blood, S2, S3, ...]
    return [(2 * i - 1) * step / 2 for i in range(num_spouses)]


def layout_subtree(unit: FamilyUnit) -> Extent:
    """Recursively layout a unit and all descendants. Returns the subtree extent."""
    # Layout each marriage's children as a group
    group_extents: list[Extent] = []
    for children in unit.spouse_children:
        if not children:
            continue
        for c in children:
            c.y = unit.y + CURRENT_GEN_H
        child_extents = [layout_subtree(c) for c in children]
        _combine_extents(child_extents, MIN_SIBLING_GAP)
        group_left = min(e.left for e in child_extents)
        group_right = max(e.right for e in child_extents)
        group_center = (group_left + group_right) / 2
        group_extents.append(Extent(group_left, group_right, group_center, children=child_extents))

    # Compute blood centre that best aligns marriage midpoints with group centres
    num_spouses = len(group_extents)
    offsets = _marriage_offsets(num_spouses)
    if group_extents:
        desired_blood_centres = [ge.center - o for ge, o in zip(group_extents, offsets)]
        blood_center = sum(desired_blood_centres) / len(desired_blood_centres)
    else:
        blood_center = 0.0

    # Shift each group so its centre sits on its marriage midpoint
    for ge, o in zip(group_extents, offsets):
        target = blood_center + o
        ge.shift(target - ge.center)

    # Resolve overlaps between groups, keeping them contiguous
    for _ in range(20):
        moved = False
        for i in range(len(group_extents) - 1):
            left_ge = group_extents[i]
            right_ge = group_extents[i + 1]
            overlap = left_ge.right + MIN_SIBLING_GAP - right_ge.left
            if overlap > 0:
                for j in range(i + 1, len(group_extents)):
                    group_extents[j].shift(overlap + 0.01)
                moved = True
        if not moved:
            break

    if group_extents:
        children_left = min(e.left for e in group_extents)
        children_right = max(e.right for e in group_extents)
    else:
        children_left = children_right = 0.0

    # Place the unit with the blood person at blood_center
    place_unit_at_blood_center(unit, blood_center, unit.y)

    unit_left = min(p.x for p in unit.people)
    unit_right = max(p.x + TEXT_W for p in unit.people)

    # If the unit extends beyond the children, expand group spacing to keep the unit
    # from overhanging too far.
    unit_width = unit_right - unit_left
    children_width = children_right - children_left
    if group_extents and unit_width > children_width:
        extra = unit_width - children_width
        n_gaps = len(group_extents) - 1
        if n_gaps > 0:
            pad = extra / n_gaps
            for i, extent in enumerate(group_extents[1:], start=1):
                extent.shift(i * pad)
            children_left = min(e.left for e in group_extents)
            children_right = max(e.right for e in group_extents)

    left = min(unit_left, children_left)
    right = max(unit_right, children_right)
    return Extent(left, right, (left + right) / 2, unit=unit, children=group_extents)


def _marriage_people(unit: FamilyUnit, spouse_idx: int) -> tuple[Person, Person]:
    """Return the left and right person of the marriage for the given spouse index."""
    if spouse_idx == 0 or spouse_idx >= len(unit.people):
        return unit.people[0], unit.people[0]

    if len(unit.people) == 2:
        return unit.people[0], unit.people[1]
    elif spouse_idx == 1:
        return unit.people[1], unit.people[0]
    elif spouse_idx == 2:
        return unit.people[0], unit.people[2]
    else:
        return unit.people[spouse_idx - 1], unit.people[spouse_idx]


def build_tree(
    root_id: str,
    generations: int,
    individuals: dict,
    families: dict,
    page_center_x: float = 600.0,
    root_y: float = 300.0,
    include_ancestors: bool = True,
    include_descendants: bool = True,
) -> tuple[list[FamilyUnit], FamilyUnit]:
    """Build all FamilyUnits, assign generation numbers, and compute x/y positions.

    Layout strategy:
    - Root generation is centred on page_center_x.
    - Ancestor generations are placed bottom-up (skipped if include_ancestors=False).
    - Descendant generations are placed top-down (skipped if include_descendants=False).
    - Overlaps within a generation are resolved by pushing units apart; we do not
      re-centre non-root generations, because that would break the vertical
      parent-child alignment.
    """
    root_spouses = get_spouses(root_id, individuals, families)
    # --- Dynamic Height Calculation ---
    # Find the tallest label in the entire dataset to ensure consistent spacing.
    all_heights = [estimate_label_height(get_name(iid, individuals), get_birth(iid, individuals)) for iid in individuals]
    global_max = max(all_heights) if all_heights else DEFAULT_TEXT_H
    
    # Update globals for this run
    global MAX_LABEL_H, CURRENT_GEN_H, MAX_LABEL_H_SMALL
    MAX_LABEL_H = global_max
    MAX_LABEL_H_SMALL = global_max - 2.0 # Keep the small offset
    # Scale generation height: 105 was for 30. Increase by the difference.
    CURRENT_GEN_H = DEFAULT_GENERATION_HEIGHT + (MAX_LABEL_H - DEFAULT_TEXT_H)
    # ---------------------------------
    root_unit = make_unit(root_id, root_spouses, individuals, generation=0)
    ancestor_gens = build_ancestors(root_id, generations, individuals, families) if include_ancestors else []
    descendant_gens = build_descendants(root_unit, generations, individuals, families) if include_descendants else []
    _sort_spouses_by_child_count(root_unit, individuals, families)
    _recompute_unit_geometry(root_unit)

    sibling_units = []
    if include_descendants and include_ancestors:
        sibling_units = [
            FamilyUnit(
                people=[Person(s, get_name(s, individuals), get_birth(s, individuals))],
                generation=0,
                width=TEXT_W,
            )
            for s in collect_siblings(root_id, individuals, families)
        ]

    # Layout root generation (root couple + siblings)
    root_generation_units = [root_unit] + sibling_units
    layout_children(page_center_x, root_generation_units, root_y)
    _resolve_overlaps(root_generation_units, page_center_x, recenter=True)

    mixed_mode = include_descendants and include_ancestors and bool(ancestor_gens)

    # If we are only showing descendants, use the recursive no-overlap layout for
    # the whole descendant tree. This guarantees no overlaps at the cost of a
    # wider chart.
    if not include_ancestors and not sibling_units:
        extent = layout_subtree(root_unit)
        dx = 20.0 - extent.left  # small left margin
        extent.shift(dx)
        all_units: list[FamilyUnit] = []
        seen_ids: set[int] = set()

        def collect(unit: FamilyUnit) -> None:
            if id(unit) in seen_ids:
                return
            seen_ids.add(id(unit))
            all_units.append(unit)
            for child in unit.children:
                collect(child)
            for group in unit.spouse_children:
                for child in group:
                    collect(child)

        collect(root_unit)
        return all_units, root_unit

    # Clear children lists; they will be repopulated below
    root_unit.children = []

    # Helper to find a person's individual centre within their unit
    def person_center(person: Person) -> float:
        return person.x + TEXT_W / 2

    # Layout ancestors from the bottom up
    y = root_y
    current_gen_units = root_generation_units
    for ancestor_gen_units in ancestor_gens:
        y -= CURRENT_GEN_H

        # Map each parent unit -> child (person, unit) pairs in current generation
        parent_to_child_pairs: dict[int, list[tuple[Person, FamilyUnit]]] = {id(u): [] for u in ancestor_gen_units}

        for unit in current_gen_units:
            for person in unit.people:
                dad, mum = get_parents(person.indi_id, individuals, families)
                key = tuple(sorted([x for x in (dad, mum) if x]))
                if not key:
                    continue
                parent_unit = next(
                    (u for u in ancestor_gen_units if tuple(sorted([p.indi_id for p in u.people if p.indi_id])) == key),
                    None,
                )
                if parent_unit:
                    parent_to_child_pairs[id(parent_unit)].append((person, unit))

        # Centre each parent unit over the midpoint of its child individuals
        for unit in ancestor_gen_units:
            pairs = parent_to_child_pairs[id(unit)]
            if pairs:
                unit.center = sum(person_center(p) for p, _ in pairs) / len(pairs)
            else:
                unit.center = page_center_x
            unit.y = y
            _apply_unit_x(unit)

        # Push apart overlaps without re-centring
        _resolve_overlaps(ancestor_gen_units, page_center_x, recenter=False)

        # Rebalance child units under their parents.  A child unit may be linked
        # from two in-law parent couples (e.g. Alexander+Elsie linked from both
        # William+Louisa and Thomas+Elizabeth).  Instead of aligning it under one
        # parent and then the other, centre it at the average of the positions
        # each parent would prefer.  This keeps shared child units in the middle.
        child_to_parent_targets: dict[int, tuple[FamilyUnit, list[tuple[float, float]]]] = {}
        for unit in ancestor_gen_units:
            for person, child_unit in parent_to_child_pairs[id(unit)]:
                entry = child_to_parent_targets.setdefault(id(child_unit), (child_unit, []))
                person_offset = person.x + TEXT_W / 2 - child_unit.center
                entry[1].append((unit.center, person_offset))

        for child_unit, targets in child_to_parent_targets.values():
            if not targets:
                continue
            if mixed_mode and len(targets) == 1:
                # In mixed charts the child generation has its own layout; only
                # rebalance child units that are shared by two in-law parents.
                continue
            desired_center = sum(parent_center - offset for parent_center, offset in targets) / len(targets)
            child_unit.center = desired_center
            child_unit.width = _unit_width(len(child_unit.people) - 1)
            _apply_unit_x(child_unit)

        # Push apart any overlaps introduced by the adjustment
        _resolve_overlaps(current_gen_units, page_center_x, recenter=False)

        # Link parents to their child units
        for unit in ancestor_gen_units:
            unit.children = []
            unit.spouse_children = [[]]
            unit.child_centers = {}
        for unit in current_gen_units:
            for person in unit.people:
                dad, mum = get_parents(person.indi_id, individuals, families)
                key = tuple(sorted([x for x in (dad, mum) if x]))
                parent_unit = next(
                    (u for u in ancestor_gen_units if tuple(sorted([p.indi_id for p in u.people if p.indi_id])) == key),
                    None,
                )
                if parent_unit and unit not in parent_unit.children:
                    parent_unit.children.append(unit)
                    parent_unit.spouse_children[0].append(unit)
                    parent_unit.child_centers[id(unit)] = person.x + TEXT_W / 2

        current_gen_units = ancestor_gen_units

    # In mixed charts, the ancestor block can end up off-centre because in-law
    # parent couples (e.g. William+Louisa and Thomas+Elizabeth) are each centred
    # over their own child person in a shared child unit.  Shift the whole
    # ancestor block so the lowest ancestor generation is centred over the
    # midpoint of the root generation.
    if mixed_mode and ancestor_gens:
        root_blood_centers = [blood_center(u) for u in root_generation_units]
        root_midpoint = (min(root_blood_centers) + max(root_blood_centers)) / 2

        lowest_ancestor_gen = ancestor_gens[-1]
        ancestor_unit_centers = [u.center for u in lowest_ancestor_gen]
        ancestor_midpoint = (min(ancestor_unit_centers) + max(ancestor_unit_centers)) / 2

        delta = root_midpoint - ancestor_midpoint
        if abs(delta) > 0.5:
            for gen in ancestor_gens:
                for unit in gen:
                    _shift_unit(unit, delta)

        # Recompute child connector endpoints now that ancestor units have been
        # shifted; the cached child_centers still reflect pre-shift positions.
        for gen in ancestor_gens:
            for parent_unit in gen:
                parent_unit.child_centers = {}
                for child_unit in parent_unit.children:
                    for person in child_unit.people:
                        dad, mum = get_parents(person.indi_id, individuals, families)
                        key = tuple(sorted([x for x in (dad, mum) if x]))
                        parent_key = tuple(sorted([p.indi_id for p in parent_unit.people if p.indi_id]))
                        if key == parent_key:
                            parent_unit.child_centers[id(child_unit)] = person.x + TEXT_W / 2
                            break

    def layout_marriage_children(parent_unit: FamilyUnit, y: float) -> None:
        """Layout children of a multi-spouse parent, keeping each marriage's children as a contiguous block."""
        groups: list[tuple[int, list[FamilyUnit], float, float, float]] = []

        for spouse_idx, children in enumerate(parent_unit.spouse_children):
            if not children:
                continue
            marriage_center = _marriage_center(parent_unit, spouse_idx)
            layout_children(marriage_center, children, y)
            left = min(c.left_x for c in children)
            right = max(c.right_x for c in children)
            groups.append((spouse_idx, children, left, right, marriage_center))

        if len(groups) <= 1:
            return

        # Sort groups left-to-right by their marriage centre
        groups.sort(key=lambda g: g[4])

        # Resolve overlaps by shifting whole groups (preserve internal layout)
        for _ in range(20):
            moved = False
            for i in range(len(groups) - 1):
                left_group = groups[i]
                right_group = groups[i + 1]
                overlap = left_group[3] + MIN_SIBLING_GAP - right_group[2]
                if overlap > 0:
                    shift = overlap + 0.01
                    for j in range(i + 1, len(groups)):
                        _, children, left, right, center = groups[j]
                        for child in children:
                            _shift_unit(child, shift)
                        groups[j] = (groups[j][0], children, left + shift, right + shift, center + shift)
                    moved = True
            if not moved:
                break

    def _marriage_center(unit: FamilyUnit, spouse_idx: int) -> float:
        """Return the x-centre of the marriage between the blood person and the given spouse."""
        if spouse_idx == 0 or spouse_idx >= len(unit.people):
            return unit.people[0].x + TEXT_W / 2

        # In the linear chain [S1, Blood, S2, S3, ...] the marriage pairs are
        # (S1,Blood), (Blood,S2), (S2,S3), ...
        if len(unit.people) == 2:
            left_person, right_person = unit.people[0], unit.people[1]
        elif spouse_idx == 1:
            left_person, right_person = unit.people[1], unit.people[0]
        elif spouse_idx == 2:
            left_person, right_person = unit.people[0], unit.people[2]
        else:
            left_person, right_person = unit.people[spouse_idx - 1], unit.people[spouse_idx]
        return (left_person.x + TEXT_W + right_person.x) / 2


    # Layout descendants from the top down
    if include_descendants:
        y = root_y
        current_gen_units = [root_unit]
        for descendant_gen_units in descendant_gens:
            y += CURRENT_GEN_H

            for parent_unit in current_gen_units:
                layout_marriage_children(parent_unit, y)

            # Flatten spouse_children into the public children list for traversal
            for parent_unit in current_gen_units:
                parent_unit.children = []
                for group in parent_unit.spouse_children:
                    parent_unit.children.extend(group)

            # Resolve overlaps between unrelated units within this generation without re-centring
            _resolve_overlaps(descendant_gen_units, page_center_x, recenter=False)

            current_gen_units = descendant_gen_units

    # Collect all units into a flat list
    all_units: list[FamilyUnit] = []
    seen_ids: set[int] = set()

    def collect(unit: FamilyUnit) -> None:
        if id(unit) in seen_ids:
            return
        seen_ids.add(id(unit))
        all_units.append(unit)
        for child in unit.children:
            collect(child)
        for group in unit.spouse_children:
            for child in group:
                collect(child)

    collect(root_unit)

    # Include root-generation siblings so their connectors and labels are rendered
    if include_descendants:
        for sibling in sibling_units:
            if id(sibling) not in seen_ids:
                seen_ids.add(id(sibling))
                all_units.append(sibling)

    # If ancestors were generated, also add any ancestor units not already in the tree
    if include_ancestors:
        for gen in ancestor_gens:
            for unit in gen:
                if id(unit) not in seen_ids:
                    seen_ids.add(id(unit))
                    all_units.append(unit)

    return all_units, root_unit


# ---------------------------------------------------------------------------
# Draw.io XML generation
# ---------------------------------------------------------------------------


def _escape_xml_attr(value: str) -> str:
    """Escape a string for use inside a double-quoted XML attribute."""
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def to_superscript(n: int) -> str:
    """Convert a non-negative integer to a Unicode superscript string."""
    if n == 0:
        return SUPERSCRIPT_DIGITS[0]
    digits = []
    while n > 0:
        digits.append(SUPERSCRIPT_DIGITS[n % 10])
        n //= 10
    return "".join(reversed(digits))


def collect_duplicate_markers(units: list[FamilyUnit]) -> dict[str, str]:
    """Return a mapping indi_id -> superscript marker for any person appearing
    more than once in the chart."""
    counts: dict[str, int] = {}
    for unit in units:
        for person in unit.people:
            counts[person.indi_id] = counts.get(person.indi_id, 0) + 1

    markers: dict[str, str] = {}
    marker_idx = 1
    for indi_id, count in counts.items():
        if count > 1:
            markers[indi_id] = to_superscript(marker_idx)
            marker_idx += 1
    return markers


def text_cell(cell_id: str, x: float, y: float, w: float, h: float, name: str, birth: str, marker: str = "") -> str:
    safe_name = _escape_xml_attr(name)
    safe_birth = _escape_xml_attr(birth)
    marker_text = _escape_xml_attr(marker)
    name_value = f"{safe_name}{marker_text}&#xa;(b. {safe_birth})" if marker_text else f"{safe_name}&#xa;(b. {safe_birth})"
    return f'''        <!-- Label {cell_id} -->
        <mxCell id="{cell_id}_bg" value="" style="shape=rect;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=none;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />
        </mxCell>
        <mxCell id="{cell_id}" value="{name_value}" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=center;verticalAlign=top;whiteSpace=wrap;rounded=0;fontSize=11;fontFamily={FONT_FAMILY};fontColor={STROKE_COLOR};" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />
        </mxCell>'''


def marriage_lines(mid: str, x1: float, x2: float, y: float) -> str:
    width = x2 - x1
    return f'''        <!-- Marriage line {mid} -->
        <mxCell id="{mid}a" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor={STROKE_COLOR};strokeWidth=1.5;" vertex="1" parent="1">
          <mxGeometry x="{x1}" y="{y}" width="{width}" height="1" as="geometry" />
        </mxCell>
        <mxCell id="{mid}b" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor={STROKE_COLOR};strokeWidth=1.5;" vertex="1" parent="1">
          <mxGeometry x="{x1}" y="{y + MARRIAGE_LINE_GAP}" width="{width}" height="1" as="geometry" />
        </mxCell>'''


def vline(vid: str, x: float, y: float, h: float) -> str:
    return f'''        <mxCell id="{vid}" value="" style="shape=rect;whiteSpace=wrap;html=1;fillColor={STROKE_COLOR};strokeColor=none;" vertex="1" parent="1">
          <mxGeometry x="{x - 1}" y="{y}" width="2" height="{h}" as="geometry" />
        </mxCell>'''


def hline(hid: str, x: float, y: float, width: float) -> str:
    return f'''        <mxCell id="{hid}" value="" style="shape=line;direction=east;whiteSpace=wrap;html=1;strokeColor={STROKE_COLOR};strokeWidth=1.5;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{width}" height="1" as="geometry" />
        </mxCell>'''


def _draw_ancestor_connectors(
    parts: list[str],
    units: list[FamilyUnit],
    h_idx_start: int,
    c_idx_start: int,
) -> tuple[int, int]:
    """Draw parent-to-child connectors for ancestor-only charts.

    Each child unit gets a horizontal connector a short distance above its text
    box, spanning the parent marriage centres.  Vertical lines descend from each
    parent couple to that bar, then a short vertical drop reaches the child.
    """
    h_idx = h_idx_start
    c_idx = c_idx_start
    v_idx = 0

    child_to_parents: dict[int, tuple[FamilyUnit, list[FamilyUnit]]] = {}
    for unit in units:
        for group in unit.spouse_children:
            for child in group:
                entry = child_to_parents.get(id(child))
                if entry is None:
                    child_to_parents[id(child)] = (child, [unit])
                elif unit not in entry[1]:
                    entry[1].append(unit)

    drawn_h: set[tuple[float, float, float]] = set()
    drawn_v: set[tuple[float, float, float]] = set()

    CHILD_DROP = 12.0
    JOIN_BAR_HALF = 15.0

    for child_obj, parents in child_to_parents.values():
        connector_y = child_obj.y - CHILD_DROP

        marriage_centers = []
        for parent in parents:
            if len(parent.people) >= 2:
                mx = (parent.people[0].x + TEXT_W + parent.people[1].x) / 2
            else:
                mx = parent.people[0].x + TEXT_W / 2
            marriage_centers.append(mx)

            top = parent.y + MAX_LABEL_H + 1.0
            h = connector_y - top
            vkey = (round(mx, 1), round(top, 1), round(h, 1))
            if vkey not in drawn_v:
                drawn_v.add(vkey)
                v_idx += 1
                parts.append(vline(f"av{v_idx}", mx, top, h))

        for mx in marriage_centers:
            left_x = mx - JOIN_BAR_HALF
            right_x = mx + JOIN_BAR_HALF
            hkey = (round(left_x, 1), round(connector_y, 1), round(right_x - left_x, 1))
            if hkey not in drawn_h:
                drawn_h.add(hkey)
                h_idx += 1
                parts.append(hline(f"ah{h_idx}", left_x, connector_y, right_x - left_x))

            drop_key = (round(mx, 1), round(connector_y + 1.0, 1), round(child_obj.y - connector_y - 1.0, 1))
            if drop_key not in drawn_v:
                drawn_v.add(drop_key)
                v_idx += 1
                parts.append(vline(f"av{v_idx}", mx, connector_y + 1.0, child_obj.y - connector_y - 1.0))

    return h_idx, c_idx


def _draw_mixed_ancestor_connectors(
    parts: list[str],
    units: list[FamilyUnit],
    h_idx_start: int,
    c_idx_start: int,
) -> tuple[int, int]:
    """Draw parent-to-child connectors for ancestor links in mixed charts.

    Each parent/child-person pair gets its own connector: a vertical descender
    from the parent couple's marriage centre to a horizontal line, then a
    horizontal line to the specific child person's centre, then a vertical drop.
    This keeps in-law connectors separate when the child unit contains spouses.
    """
    h_idx = h_idx_start
    c_idx = c_idx_start
    v_idx = 0

    drawn_h: set[tuple[float, float, float]] = set()
    drawn_v: set[tuple[float, float, float]] = set()

    CHILD_DROP = 12.0

    for parent in units:
        for group in parent.spouse_children:
            for child in group:
                child_center = parent.child_centers.get(id(child), blood_center(child))
                connector_y = child.y - CHILD_DROP

                if len(parent.people) >= 2:
                    mx = (parent.people[0].x + TEXT_W + parent.people[1].x) / 2
                else:
                    mx = parent.people[0].x + TEXT_W / 2

                top = parent.y + MAX_LABEL_H + 1.0
                h = connector_y - top
                vkey = (round(mx, 1), round(top, 1), round(h, 1))
                if vkey not in drawn_v:
                    drawn_v.add(vkey)
                    v_idx += 1
                    parts.append(vline(f"av{v_idx}", mx, top, h))

                if abs(mx - child_center) > 0.5:
                    left = min(mx, child_center)
                    right = max(mx, child_center)
                    hkey = (round(left, 1), round(connector_y, 1), round(right - left, 1))
                    if hkey not in drawn_h:
                        drawn_h.add(hkey)
                        h_idx += 1
                        parts.append(hline(f"ah{h_idx}", left, connector_y, right - left))

                drop_key = (round(child_center, 1), round(connector_y + 1.0, 1), round(child.y - connector_y - 1.0, 1))
                if drop_key not in drawn_v:
                    drawn_v.add(drop_key)
                    v_idx += 1
                    parts.append(vline(f"av{v_idx}", child_center, connector_y + 1.0, child.y - connector_y - 1.0))

    return h_idx, c_idx


def generate_drawio(units: list[FamilyUnit], title: str, ancestor_mode: bool = False, individuals: dict | None = None) -> str:
    parts: list[str] = []

    # Detect any individual appearing more than once (pedigree collapse)
    duplicate_markers = collect_duplicate_markers(units)

    # Compute content bounding box and shift so the diagram sits tightly on the page
    min_x = min(p.x for u in units for p in u.people)
    max_x = max(p.x + TEXT_W for u in units for p in u.people)
    min_y = min(u.y for u in units)
    max_gen = max((u.generation for u in units), default=0)
    max_y = max(u.y + (MAX_LABEL_H_SMALL if u.generation == max_gen else MAX_LABEL_H) for u in units)

    content_width = max_x - min_x
    content_height = max_y - min_y
    title_height = 22.0
    margin = 20.0

    dx = margin - min_x
    dy = margin + title_height - min_y

    page_width = content_width + 2 * margin
    page_height = content_height + title_height + 2 * margin

    # Shift all units/persons in place
    for unit in units:
        unit.y += dy
        unit.center += dx
        for person in unit.people:
            person.x += dx
        for key in unit.child_centers:
            unit.child_centers[key] += dx

    parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="drawio" version="26.0.0">
  <diagram name="Family Tree">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_width}" pageHeight="{page_height}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />''')

    safe_title = _escape_xml_attr(title)
    parts.append(f'''
        <!-- Title -->
        <mxCell id="title" value="{safe_title}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=14;fontFamily={FONT_FAMILY};fontStyle=1" vertex="1" parent="1">
          <mxGeometry x="{margin}" y="{margin / 2}" width="{content_width}" height="{title_height}" as="geometry" />
        </mxCell>''')

    units_by_gen: dict[int, list[FamilyUnit]] = {}
    for unit in units:
        units_by_gen.setdefault(unit.generation, []).append(unit)

    # Marriage lines (drawn first so labels sit on top)
    parts.append("\n        <!-- Marriage lines -->")
    m_idx = 0
    for unit in units:
        num_spouses = len(unit.people) - 1
        if num_spouses <= 0:
            continue
        if num_spouses == 1:
            pairs = [(0, 1)]
        else:
            # [S1, Blood, S2, S3, ...] -> adjacent pairs are (S1,Blood), (Blood,S2), (S2,S3), ...
            pairs = [(1, 0), (0, 2)] + [(i, i + 1) for i in range(2, num_spouses)]
        for pair_idx, (a, b) in enumerate(pairs):
            m_idx += 1
            left_person = unit.people[a]
            right_person = unit.people[b]
            x1 = left_person.x + TEXT_W
            x2 = right_person.x
            if x2 < x1:
                x1, x2 = x2, x1
            # Marriage lines for all spouses stay at the same height.
            y = unit.y + MARRIAGE_Y_OFFSET
            parts.append(marriage_lines(f"m{m_idx}", x1, x2, y))

    # Child connectors and descenders
    # Child connectors and descenders (drawn before labels so labels sit on top)
    parts.append("\n        <!-- Child connectors and descenders -->")
    h_idx = 0
    c_idx = 0

    if ancestor_mode:
        h_idx, c_idx = _draw_ancestor_connectors(parts, units, h_idx, c_idx)
    else:
        # Mixed mode: draw ancestor links with per-child connectors, then
        # descendant links with the normal descendant-style connectors.
        ancestor_units = [u for u in units if u.generation < 0]
        if ancestor_units:
            h_idx, c_idx = _draw_mixed_ancestor_connectors(parts, ancestor_units, h_idx, c_idx)

        for unit in units:
            if unit.generation < 0:
                continue

            # Gather non-empty child groups with their geometry.
            group_infos = []
            for spouse_idx, group in enumerate(unit.spouse_children):
                if not group:
                    continue
                left_center = min(blood_center(c) for c in group)
                right_center = max(blood_center(c) for c in group)
                group_infos.append({
                    "spouse_idx": spouse_idx,
                    "group": group,
                    "center": (left_center + right_center) / 2,
                    "left_center": left_center,
                    "right_center": right_center,
                })
            if not group_infos:
                continue

            # Sort groups left-to-right so their child connectors step down naturally.
            group_infos.sort(key=lambda g: g["center"])

            marriage_line_bottom = unit.y + MARRIAGE_Y_OFFSET + MARRIAGE_LINE_GAP + 1.0

            for gi in group_infos:
                spouse_idx = gi["spouse_idx"]
                # Marriage midpoint: the two people that form the marriage.
                if spouse_idx == 0 or spouse_idx >= len(unit.people):
                    left_person = unit.people[0]
                    right_person = unit.people[0]
                    descender_top = unit.y + MAX_LABEL_H
                elif len(unit.people) == 2:
                    left_person = unit.people[0]
                    right_person = unit.people[1]
                    descender_top = marriage_line_bottom
                elif spouse_idx == 1:
                    left_person = unit.people[1]   # S1
                    right_person = unit.people[0]  # Blood
                    descender_top = marriage_line_bottom
                elif spouse_idx == 2:
                    left_person = unit.people[0]   # Blood
                    right_person = unit.people[2]  # S2
                    descender_top = marriage_line_bottom
                else:
                    left_person = unit.people[spouse_idx - 1]
                    right_person = unit.people[spouse_idx]
                    descender_top = marriage_line_bottom
                gi["marriage_x"] = (left_person.x + TEXT_W + right_person.x) / 2
                gi["descender_top"] = descender_top
                gi["is_single"] = (spouse_idx == 0 or spouse_idx >= len(unit.people))

            # Stagger the horizontal child connectors vertically. The rightmost group gets
            # the highest connector; each group to the left steps down a little. This keeps
            # descenders from crossing each other or other connectors.
            # Keep the connectors below the parent text boxes so they do not overlap labels.
            # Single-parent descenders are deliberately shorter than couple descenders.
            desired_lengths = [
                45.0 if gi["is_single"] else 63.0 for gi in group_infos
            ]
            base_connector_y = max(
                gi["descender_top"] + length
                for gi, length in zip(group_infos, desired_lengths)
            )
            base_connector_y = max(base_connector_y, unit.y + MAX_LABEL_H + 45.0) - 40.0
            child_y = group_infos[0]["group"][0].y
            max_connector_y = base_connector_y + (len(group_infos) - 1) * CHILD_CONNECTOR_STAGGER
            if max_connector_y >= child_y - 12.0 and len(group_infos) > 1:
                available = max(0.0, child_y - 12.0 - base_connector_y)
                stagger = available / (len(group_infos) - 1)
            else:
                stagger = CHILD_CONNECTOR_STAGGER

            n_groups = len(group_infos)
            for stagger_idx, gi in enumerate(group_infos):
                h_idx += 1
                # group_infos is sorted left-to-right; rightmost gets the highest (smallest y)
                connector_y = base_connector_y + (n_groups - 1 - stagger_idx) * stagger
                marriage_x = gi["marriage_x"]
                descender_top = gi["descender_top"]
                left_center = gi["left_center"]
                right_center = gi["right_center"]

                # The horizontal connector must always reach the marriage descender, even
                # when the children sit far to the side of the marriage line.
                conn_left = min(marriage_x, left_center)
                conn_right = max(marriage_x, right_center)
                if conn_right - conn_left > 0.5:
                    parts.append(hline(f"h{h_idx}", conn_left, connector_y, conn_right - conn_left))

                parts.append(vline(f"v{h_idx}", marriage_x, descender_top, connector_y + 1.0 - descender_top))

                for child in gi["group"]:
                    c_idx += 1
                    # Stop the child drop just below the horizontal connector so it reads as one
                    # continuous line, but keep it clear of the child's text.
                    parts.append(vline(f"c{c_idx}", blood_center(child), connector_y + 1.0, child.y - connector_y - 4.0))

    # Person labels (drawn on top of all connector lines)
    id_counter: dict[str, int] = {}
    for gen in sorted(units_by_gen.keys()):
        parts.append(f"\n        <!-- Generation {gen} -->")
        for unit in units_by_gen[gen]:
            h = MAX_LABEL_H_SMALL if gen == max_gen else MAX_LABEL_H
            for person in unit.people:
                birth = person.birth or "?"
                count = id_counter.get(person.indi_id, 0) + 1
                id_counter[person.indi_id] = count
                cell_id = person.indi_id if count == 1 else f"{person.indi_id}_{count}"
                marker = duplicate_markers.get(person.indi_id, "")
                parts.append(text_cell(cell_id, person.x, unit.y, TEXT_W, h, person.name, birth, marker))

    # Legend for duplicate persons
    if duplicate_markers:
        # Sort by the numeric value represented by the marker for readability
        def marker_sort_key(item: tuple[str, str]) -> int:
            marker = item[1]
            total = 0
            for ch in marker:
                idx = SUPERSCRIPT_DIGITS.find(ch)
                if idx >= 0:
                    total = total * 10 + idx
            return total
        sorted_markers = sorted(duplicate_markers.items(), key=marker_sort_key)
        legend_text = "; ".join(f"{get_name(indi_id, individuals or {})} {marker}" for indi_id, marker in sorted_markers)
        # Use a compact note instead of listing every name if many
        if len(duplicate_markers) <= 5:
            legend_value = f"Duplicate persons: {legend_text}"
        else:
            legend_value = f"Superscript numbers indicate the same person appearing in multiple positions ({len(set(duplicate_markers.values()))} duplicated individuals)."
        safe_legend = _escape_xml_attr(legend_value)
        parts.append(f'''
        <!-- Duplicate-person legend -->
        <mxCell id="legend" value="{safe_legend}" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;fontSize=9;fontFamily={FONT_FAMILY};fontColor={STROKE_COLOR};" vertex="1" parent="1">
          <mxGeometry x="{margin}" y="{page_height - margin + 5}" width="{content_width}" height="{margin - 5}" as="geometry" />
        </mxCell>''')

    parts.append('''
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>''')

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a visitation-style family tree from GEDCOM.")
    parser.add_argument("--gedcom", required=True, help="Path to the GEDCOM file.")
    parser.add_argument("--root", default=None, help='Focus person, e.g. "Brian Stanley Short" (given surname).')
    parser.add_argument("--root-id", default=None, help='Focus person ID, e.g. "@I123@" (overrides --root).')
    parser.add_argument("--generations", type=int, default=2, help="Number of generations up and down from root (default 2).")
    parser.add_argument("--all-descendants", action="store_true", help="Use the maximum descendant depth as --generations.")
    parser.add_argument("--descendants-only", action="store_true", help="Skip ancestors; show only root and descendants.")
    parser.add_argument("--ancestors-only", action="store_true", help="Skip descendants; show only root and ancestors.")
    parser.add_argument("--output", default="family_tree.drawio", help="Output draw.io file path.")
    parser.add_argument("--title", default=None, help="Diagram title (default derived from root name).")
    parser.add_argument("--font-family", default="Helvetica", help="Font family for labels and title (default Helvetica).")
    parser.add_argument("--center-x", type=float, default=600.0, help="Horizontal centre of the diagram (default 600).")
    parser.add_argument("--root-y", type=float, default=300.0, help="Y position of the root generation (default 300).")
    args = parser.parse_args()

    global FONT_FAMILY
    FONT_FAMILY = args.font_family

    if not args.root and not args.root_id:
        print("ERROR: provide --root or --root-id", file=sys.stderr)
        return 1

    individuals, families = parse_gedcom(args.gedcom)

    if args.root_id:
        root_id = args.root_id
        if root_id not in individuals:
            print(f"ERROR: Could not find root ID '{root_id}' in {args.gedcom}", file=sys.stderr)
            return 1
    else:
        parts = args.root.split()
        if len(parts) < 2:
            print("ERROR: --root should be 'Given Surname'", file=sys.stderr)
            return 1
        surname = parts[-1]
        given = " ".join(parts[:-1])

        root_id = find_individual_by_name(individuals, given, surname)
        if not root_id:
            print(f"ERROR: Could not find '{args.root}' in {args.gedcom}", file=sys.stderr)
            return 1

    if args.all_descendants:
        max_depth = 0
        visited: set[str] = set()
        queue = [(root_id, 0)]
        while queue:
            indi_id, depth = queue.pop(0)
            if indi_id in visited:
                continue
            visited.add(indi_id)
            max_depth = max(max_depth, depth)
            for child_id in get_children(indi_id, individuals, families):
                if child_id not in visited:
                    queue.append((child_id, depth + 1))
        args.generations = max_depth
        print(f"Auto-detected descendant depth: {max_depth}")

    print(f"Root: {get_name(root_id, individuals)} ({root_id})")

    units, root_unit = build_tree(
        root_id,
        args.generations,
        individuals,
        families,
        page_center_x=args.center_x,
        root_y=args.root_y,
        include_ancestors=not args.descendants_only,
        include_descendants=not args.ancestors_only,
    )

    title = args.title or f"{get_name(root_id, individuals)} Family Tree (Visitation Style)"
    xml = generate_drawio(units, title, ancestor_mode=args.ancestors_only, individuals=individuals)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"Wrote {len(units)} units to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
