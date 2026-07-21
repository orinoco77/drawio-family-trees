#!/usr/bin/env python3
"""
Fix unescaped double quotes inside draw.io value attributes.

Some GEDCOM files contain names with quoted nicknames such as
`John Henry "Jack" Irvine`. If the generator emits these raw inside a
double-quoted XML attribute, the resulting `.drawio` file is not well-formed
and tools like `verify_family_tree.py` will fail to parse it.

This script rewrites value="..." attributes so any raw double quotes inside
are escaped as &quot;. It is idempotent and leaves correctly-escaped files
unchanged.

Usage:
    python3 fix_drawio_value_quotes.py family_tree.drawio

The file is updated in place and a summary is printed to stdout.
"""

import argparse
import re
import sys
from pathlib import Path


def fix_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")

    def _fix_attr(match: re.Match) -> str:
        prefix = match.group(1)  # value="
        inner = match.group(2)
        # Escape any raw double quotes; do not double-escape existing &quot;.
        inner = inner.replace("&quot;", "\x00QUOTE\x00")
        inner = inner.replace('"', "&quot;")
        inner = inner.replace("\x00QUOTE\x00", "&quot;")
        return prefix + inner + '"'

    # Match value="..." where the closing quote is immediately before a space
    # followed by another attribute (e.g. style=). This avoids matching across
    # unrelated content.
    fixed = re.sub(r'(value=")(.*?)"(?=\s+\w+=)', _fix_attr, original)

    if fixed == original:
        print(f"No raw double quotes found in {path}; no changes made.")
        return 0

    path.write_text(fixed, encoding="utf-8")

    changed = sum(1 for a, b in zip(original, fixed) if a != b)
    print(f"Fixed unescaped double quotes in {path} ({changed} characters changed).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Escape raw double quotes inside draw.io value attributes."
    )
    parser.add_argument("drawio", help="Path to the .drawio file to fix in place.")
    args = parser.parse_args()
    return fix_file(Path(args.drawio))


if __name__ == "__main__":
    raise SystemExit(main())
