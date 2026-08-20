#!/usr/bin/env python3
"""Probe the Edward Grey chart to measure the parent-to-sibling-bar drop
after a DESCENDER_OFFSET tweak.

Run this after editing DESCENDER_OFFSET in drawio_layout.py and regenerating
the chart to confirm the new gap matches expectations.

Usage:
    python3 scripts/test_descender_offset.py /path/to/chart.drawio
"""
import re
import sys
from pathlib import Path


def measure(path: Path) -> tuple[float, float, int]:
    xml = path.read_text()
    v_pattern = re.compile(r'id="(v\d+)".*?x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', re.S)
    h_pattern = re.compile(r'id="(h\d+)".*?x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="1"', re.S)
    labels = re.findall(
        r'<mxCell id="(@\w+@)" value="([^"]+)"[^>]*?><mxGeometry x="([\d.]+)" y="([\d.]+)" width="75" height="(\d+)"',
        xml,
    )
    v_lines = v_pattern.findall(xml)
    h_lines = h_pattern.findall(xml)
    if not v_lines or not h_lines or not labels:
        raise SystemExit("Could not parse chart elements")

    bar_y = float(h_lines[0][2])
    descender_height = float(v_lines[0][4])
    root_h = float(labels[0][4])
    return descender_height, bar_y, root_h


def main():
    path = Path(sys.argv[1])
    h, bar_y, root_h = measure(path)
    print(f"Parent-to-sibling-bar drop (v-line height): {h:.0f} px")
    print(f"Sibling bar y: {bar_y:.0f}, root label height: {root_h:.0f}")
    print(f"Effective gap from parent label bottom to bar: {bar_y - root_h:.0f} px")


if __name__ == "__main__":
    main()
