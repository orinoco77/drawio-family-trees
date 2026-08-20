#!/usr/bin/env python3
"""
Export a draw.io family tree to PNG without the drawio CLI's wide-image
stretching bug.

Draw.io's direct PNG exporter sometimes renders only a small slice of very wide
diagrams and stretches it to the target dimensions. This script sidesteps the
problem by exporting to PDF first, then converting the PDF to PNG with
`pdftoppm`.

Usage:
    python3 scripts/export_png.py chart.drawio chart.png [--dpi 150]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write(f"Command failed: {' '.join(cmd)}\n")
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result


def export_png(input_path: Path, output_path: Path, dpi: int) -> None:
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    drawio = shutil.which("drawio")
    if drawio is None:
        raise SystemExit("drawio CLI not found in PATH")

    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise SystemExit("pdftoppm not found in PATH (install poppler-utils)")

    with tempfile.TemporaryDirectory(prefix="drawio_export_") as tmpdir:
        pdf_path = Path(tmpdir) / "chart.pdf"
        run([
            drawio,
            "--export",
            "--format", "pdf",
            "--output", str(pdf_path),
            str(input_path),
        ])

        # pdftoppm writes <prefix>-1.png for a single-page PDF.
        prefix = Path(tmpdir) / "page"
        run([
            pdftoppm,
            "-png",
            "-r", str(dpi),
            str(pdf_path),
            str(prefix),
        ])

        candidates = list(prefix.parent.glob(f"{prefix.name}*.png"))
        if not candidates:
            raise SystemExit("pdftoppm produced no PNG output")

        candidates.sort()
        candidates[0].replace(output_path)

    print(f"{input_path} -> {output_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export draw.io chart to PNG via PDF")
    parser.add_argument("input", type=Path, help="Input .drawio file")
    parser.add_argument("output", type=Path, help="Output .png file")
    parser.add_argument("--dpi", type=int, default=150, help="PNG resolution (default: 150)")
    args = parser.parse_args(argv)

    export_png(args.input, args.output, args.dpi)


if __name__ == "__main__":
    main()
