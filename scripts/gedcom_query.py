#!/usr/bin/env python3
"""Compact GEDCOM query tool — the ONLY way the agent should inspect a GEDCOM.

The Short GEDCOM is ~12 MB. Reading or grepping it directly pulls enormous
amounts of text into the agent context. This tool answers every question the
chart workflow needs with a few lines of output instead:

    gedcom_query.py <ged> stats
    gedcom_query.py <ged> search <pattern> [--limit N]
    gedcom_query.py <ged> show <@I...@>
    gedcom_query.py <ged> tree <@I...@> [--down N | --up N]

The parsed GEDCOM is cached under ~/.cache/drawio-family-trees/ keyed by
path+mtime+size, so repeat queries are instant.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_gedcom import (  # noqa: E402
    parse_gedcom,
    get_name,
    get_parents,
    get_children,
    get_spouses,
)

CACHE_DIR = Path.home() / ".cache" / "drawio-family-trees"
YEAR_RE = re.compile(r"(\d{4})")


def load(path: str):
    """Parse the GEDCOM, using a pickle cache keyed by path+mtime+size."""
    ap = os.path.abspath(path)
    st = os.stat(ap)
    key = hashlib.sha1(f"{ap}|{st.st_mtime_ns}|{st.st_size}".encode()).hexdigest()[:16]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.pkl"
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    data = parse_gedcom(ap)
    tmp = cache_file.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(data, f)
    tmp.replace(cache_file)
    return data


def year(date_str: str) -> str:
    m = YEAR_RE.search(date_str or "")
    return m.group(1) if m else ""


def lifespans(d: dict) -> str:
    b, dd = year(d.get("birth", "")), year(d.get("death", ""))
    if not b and not dd:
        return ""
    return f" ({b}–{dd})" if dd else f" (b. {b})"


def one_liner(indi_id: str, individuals: dict) -> str:
    d = individuals.get(indi_id, {})
    return f"{get_name(indi_id, individuals)}{lifespans(d)} {indi_id}"


def cmd_stats(individuals, families):
    named = sum(1 for d in individuals.values() if d.get("name") or d.get("givn"))
    print(f"individuals: {len(individuals)} ({named} named), families: {len(families)}")


def cmd_search(individuals, pattern: str, limit: int):
    words = pattern.lower().split()
    hits = [
        iid
        for iid in individuals
        if all(w in get_name(iid, individuals).lower() for w in words)
    ]
    # Sort by birth year so same-name people are easy to disambiguate.
    hits.sort(key=lambda i: year(individuals[i].get("birth", "")) or "9999")
    print(f"{len(hits)} match(es) for '{pattern}':")
    for iid in hits[:limit]:
        print(f"  {one_liner(iid, individuals)}")
    if len(hits) > limit:
        print(f"  … {len(hits) - limit} more (raise --limit)")
    if hits:
        print("next: show <id>  |  tree <id> --down N")


def cmd_show(indi_id, individuals, families):
    if indi_id not in individuals:
        print(f"not found: {indi_id}")
        return 1
    d = individuals[indi_id]
    print(one_liner(indi_id, individuals))
    if d.get("sex"):
        print(f"  sex: {d['sex']}")
    if d.get("birth"):
        print(f"  born: {d['birth']}")
    if d.get("death"):
        print(f"  died: {d['death']}")
    f, m = get_parents(indi_id, individuals, families)
    if f or m:
        print(f"  father: {one_liner(f, individuals) if f else '?'}")
        print(f"  mother: {one_liner(m, individuals) if m else '?'}")
    for s in get_spouses(indi_id, individuals, families):
        print(f"  spouse: {one_liner(s, individuals)}")
    kids = get_children(indi_id, individuals, families)
    if kids:
        print(f"  children ({len(kids)}):")
        for c in kids:
            print(f"    {one_liner(c, individuals)}")
    return 0


def _down(indi_id, individuals, families, depth, prefix, out, seen):
    d = individuals.get(indi_id, {})
    spouses = get_spouses(indi_id, individuals, families)
    line = f"{get_name(indi_id, individuals)}{lifespans(d)} {indi_id}"
    if spouses:
        line += " & " + " & ".join(get_name(s, individuals) for s in spouses)
    out.append(prefix + line)
    if depth <= 0 or indi_id in seen:
        return
    seen.add(indi_id)
    for c in get_children(indi_id, individuals, families):
        _down(c, individuals, families, depth - 1, prefix + "  ", out, seen)


def _up(indi_id, individuals, families, depth, prefix, out, seen):
    d = individuals.get(indi_id, {})
    out.append(f"{prefix}{get_name(indi_id, individuals)}{lifespans(d)} {indi_id}")
    if depth <= 0 or indi_id in seen:
        return
    seen.add(indi_id)
    f, m = get_parents(indi_id, individuals, families)
    for p in (f, m):
        if p:
            _up(p, individuals, families, depth - 1, prefix + "  ", out, seen)


def cmd_tree(indi_id, individuals, families, down, up):
    if indi_id not in individuals:
        print(f"not found: {indi_id}")
        return 1
    out: list[str] = []
    if up is not None:
        _up(indi_id, individuals, families, up, "", out, set())
        direction = f"ancestors (depth {up})"
    else:
        _down(indi_id, individuals, families, down, "", out, set())
        direction = f"descendants (depth {down})"
    print(f"{direction} of {one_liner(indi_id, individuals)} — {len(out)} people:")
    for line in out:
        print(line)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gedcom")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    p = sub.add_parser("search")
    p.add_argument("pattern")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("show")
    p.add_argument("id")
    p = sub.add_parser("tree")
    p.add_argument("id")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--down", type=int, default=None)
    g.add_argument("--up", type=int, default=None)
    args = ap.parse_args()

    individuals, families = load(args.gedcom)
    if args.cmd == "stats":
        cmd_stats(individuals, families)
    elif args.cmd == "search":
        cmd_search(individuals, args.pattern, args.limit)
    elif args.cmd == "show":
        return cmd_show(args.id, individuals, families) or 0
    elif args.cmd == "tree":
        down = args.down if args.down is not None else (2 if args.up is None else None)
        return cmd_tree(args.id, individuals, families, down, args.up) or 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
