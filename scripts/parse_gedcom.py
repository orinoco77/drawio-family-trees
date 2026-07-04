#!/usr/bin/env python3
"""
Minimal GEDCOM 5.5.1 parser for family-tree generation.

Reads a GEDCOM file and produces:
- individuals: dict keyed by @I... pointers
- families:    dict keyed by @F... pointers

Each individual contains name, given name, surname, sex, birth date,
family-of-origin (famc), and families-as-spouse (fams).
"""

from __future__ import annotations


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
    name = d.get("name", "").replace("/", "")
    if not name:
        name = f"{d.get('givn', '')} {d.get('surn', '')}".strip()
    return name or indi_id


def get_birth(indi_id: str, individuals: dict) -> str:
    return individuals.get(indi_id, {}).get("birth", "")


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
    """Return the first individual whose given name contains `given` and surname matches."""
    for indi_id, data in individuals.items():
        if surname == data.get("surn", "") and given in data.get("givn", ""):
            return indi_id
    return None


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "example.ged"
    individuals, families = parse_gedcom(path)
    print(f"Loaded {len(individuals)} individuals and {len(families)} families from {path}")
