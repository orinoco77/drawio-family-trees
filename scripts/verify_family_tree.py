#!/usr/bin/env python3
"""Verify a generated visitation-style family tree before delivery.

Checks:
1. Structural linter returns 0 errors and 0 warnings.
2. Labels are distributed across one distinct y-value per generation.
3. Horizontal child connectors from different parent units do not overlap
   horizontally at the same or near-same y-level (a common symptom of
   conjoined families in descendant charts).

Exit code 0 if all checks pass, non-zero otherwise.
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def run_validate(drawio_path: str) -> tuple[int, int, str]:
    """Run the structural linter and return (errors, warnings, raw_output)."""
    # Prefer the linter bundled with this skill so the skill is self-contained.
    validate_script = (
        Path(__file__).resolve().parent / "validate.py"
    )
    if not validate_script.exists():
        # Fall back to the parent drawio-skill location.
        validate_script = (
            Path.home()
            / ".hermes"
            / "skills"
            / "drawio-skill"
            / "skills"
            / "drawio-skill"
            / "scripts"
            / "validate.py"
        )
    if not validate_script.exists():
        # Older sibling location in the drawio-skill tree.
        validate_script = (
            Path.home()
            / ".hermes"
            / "skills"
            / "drawio-skill"
            / "drawio-family-trees"
            / "scripts"
            / "validate.py"
        )
    result = subprocess.run(
        [sys.executable, str(validate_script), drawio_path],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    errors = 0
    warnings = 0
    for line in output.splitlines():
        if "error(s)" in line and "warning(s)" in line:
            parts = line.replace(",", "").split()
            for i, p in enumerate(parts):
                if p == "error(s),":
                    errors = int(parts[i - 1])
                if p == "warning(s)":
                    warnings = int(parts[i - 1])
    return errors, warnings, output


def count_generations(drawio_path: str) -> int:
    """Return the number of distinct label y-values (proxy for generations)."""
    tree = ET.parse(drawio_path)
    ys = set()
    for cell in tree.iter("mxCell"):
        value = cell.get("value", "")
        geom = cell.find("mxGeometry")
        if geom is None or not value or "Family Tree" in value:
            continue
        ys.add(float(geom.get("y", 0)))
    return len(ys)


def find_connector_overlaps(
    drawio_path: str, y_tolerance: float = 3.0
) -> list[tuple[str, str, float, float, float, float, float]]:
    """Find horizontal child connectors that overlap horizontally within y_tolerance."""
    tree = ET.parse(drawio_path)
    h_lines = []
    for cell in tree.iter("mxCell"):
        cell_id = cell.get("id", "")
        style = cell.get("style", "")
        geom = cell.find("mxGeometry")
        if geom is None or "shape=line;direction=east" not in style:
            continue
        x = float(geom.get("x", 0))
        y = float(geom.get("y", 0))
        w = float(geom.get("width", 0))
        if cell_id.startswith("h") and w > 5:
            h_lines.append((cell_id, y, x, x + w))

    overlaps = []
    for i, (id1, y1, x1a, x1b) in enumerate(h_lines):
        for j, (id2, y2, x2a, x2b) in enumerate(h_lines):
            if i >= j:
                continue
            if abs(y1 - y2) <= y_tolerance and not (x1b < x2a or x2b < x1a):
                overlaps.append((id1, id2, y1, y2, x1a, x1b, x2a, x2b))
    return overlaps


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <family_tree.drawio>", file=sys.stderr)
        return 2

    drawio_path = sys.argv[1]
    ok = True

    print(f"Verifying {drawio_path}\n")

    errors, warnings, lint_output = run_validate(drawio_path)
    print("1. Structural linter")
    if errors == 0 and warnings == 0:
        print("   OK: 0 error(s), 0 warning(s)")
    else:
        ok = False
        print(f"   FAIL: {errors} error(s), {warnings} warning(s)")
        print("   Linter output:")
        for line in lint_output.splitlines():
            print(f"      {line}")

    generations = count_generations(drawio_path)
    print(f"\n2. Generational separation")
    print(f"   Distinct label y-values: {generations}")
    if generations < 3:
        ok = False
        print("   FAIL: labels are collapsed onto too few horizontal lines")

    overlaps = find_connector_overlaps(drawio_path)
    print(f"\n3. Connector overlap check")
    if not overlaps:
        print("   OK: no overlapping horizontal child connectors")
    else:
        ok = False
        print(f"   FAIL: {len(overlaps)} overlapping connector pair(s)")
        for id1, id2, y1, y2, x1a, x1b, x2a, x2b in overlaps[:10]:
            print(
                f"      {id1} (y={y1:.1f}, x={x1a:.1f}-{x1b:.1f}) overlaps "
                f"{id2} (y={y2:.1f}, x={x2a:.1f}-{x2b:.1f})"
            )

    print()
    if ok:
        print("All checks passed. The chart is safe to deliver.")
        return 0
    print("Some checks failed. Do not deliver the chart without fixing the issues above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
