#!/usr/bin/env python3
"""Render a .drawio file to PNG and/or SVG via a local draw.io renderer.

Post-processes the exported files so they have solid white backgrounds:
- SVG: injects a white <rect> as the first child of the root <g>.
- PNG: composites any alpha channel onto white and saves as plain RGB.

If scale=2 fails (common for very wide charts), automatically falls back to
scale=1 for the PNG. The SVG is always attempted at scale=1 because SVG is
resolution-independent.

Expects a draw.io renderer at http://localhost:8080/convert_file.
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required for PNG flattening: pip install Pillow") from exc


def render(input_path: Path, fmt: str, scale: int) -> bytes:
    accept = {
        "png": "image/png",
        "svg": "image/svg+xml; charset=utf-8",
    }[fmt]
    url = f"http://localhost:8080/convert_file?border=10&scale={scale}"
    import urllib.request

    req = urllib.request.Request(
        url,
        data=input_path.read_bytes(),
        headers={"Content-Type": "application/xml", "Accept": accept},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def add_svg_background(svg: str) -> str:
    m = re.search(r'width="(\d+)px"\s+height="(\d+)px"\s+viewBox="([^"]+)"', svg)
    if not m:
        return svg
    w, h = int(m.group(1)), int(m.group(2))
    vb = m.group(3).split()
    x, y = float(vb[0]), float(vb[1])
    rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" stroke="none"/>'
    pos = svg.find("<g>")
    if pos == -1:
        return svg
    return svg[: pos + 3] + rect + svg[pos + 3 :]


def flatten_png(png_bytes: bytes) -> bytes:
    from io import BytesIO

    img = Image.open(BytesIO(png_bytes))
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a draw.io family tree to PNG/SVG with white background.")
    parser.add_argument("input", type=Path, help="Input .drawio file")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output base path (default: same as input)")
    parser.add_argument("--scale", type=int, default=2, help="PNG render scale (default: 2)")
    parser.add_argument("--png", action="store_true", help="Render PNG")
    parser.add_argument("--svg", action="store_true", help="Render SVG")
    args = parser.parse_args()

    if not args.png and not args.svg:
        args.png = args.svg = True

    base = args.output or args.input.with_suffix("")
    input_path: Path = args.input

    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 1

    if args.svg:
        svg_path = base.with_suffix(".svg")
        try:
            svg_bytes = render(input_path, "svg", scale=1)
            svg_text = svg_bytes.decode("utf-8", errors="replace")
            if not svg_text.lstrip().startswith("<?xml"):
                print(f"WARNING: SVG render did not return XML; skipping SVG.\n{svg_text[:500]}", file=sys.stderr)
            else:
                svg_path.write_text(add_svg_background(svg_text), encoding="utf-8")
                print(f"Wrote SVG: {svg_path}")
        except Exception as exc:  # pragma: no cover
            print(f"ERROR: SVG render failed: {exc}", file=sys.stderr)

    if args.png:
        png_path = base.with_suffix(".png")
        for scale in (args.scale, 1):
            try:
                png_bytes = render(input_path, "png", scale=scale)
                if len(png_bytes) == 0:
                    raise RuntimeError("renderer returned empty PNG")
                png_path.write_bytes(flatten_png(png_bytes))
                print(f"Wrote PNG: {png_path} (scale={scale})")
                break
            except Exception as exc:
                if scale == 1:
                    print(f"ERROR: PNG render failed at scale={scale}: {exc}", file=sys.stderr)
                    return 1
                print(f"WARNING: PNG render failed at scale={scale}, falling back to scale=1: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
