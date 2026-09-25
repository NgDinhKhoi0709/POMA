#!/usr/bin/env python3
"""Render pages of a compiled Typst-generated PDF deck to PNG for visual inspection.

Typst gives no warning when slide content overflows onto a silent extra page. This
script is step 3 of the verification loop described in the typst-slide skill: after
`typst compile deck.typ deck.pdf`, run this to rasterize the pages you need to check,
then use the Read tool on the resulting PNGs to actually look at them.

Usage:
    python render_pages.py deck.pdf                       # render every page to ./render/
    python render_pages.py deck.pdf out_dir --dpi 110      # custom output dir + resolution
    python render_pages.py deck.pdf --pages 3,4,12         # only specific 1-indexed pages
    python render_pages.py deck.pdf --start 5 --end 9      # a 1-indexed page range

Requires PyMuPDF (`pip install pymupdf`); no other dependencies.
"""
import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", help="path to the compiled PDF")
    ap.add_argument("outdir", nargs="?", default="render", help="output directory (default: ./render)")
    ap.add_argument("--dpi", type=int, default=90, help="render resolution (default: 90; use 110+ to zoom in on small text)")
    ap.add_argument("--pages", help="comma-separated 1-indexed page numbers, e.g. 3,4,12")
    ap.add_argument("--start", type=int, help="1-indexed first page of a range")
    ap.add_argument("--end", type=int, help="1-indexed last page of a range (inclusive)")
    args = ap.parse_args()

    try:
        import fitz  # PyMuPDF
    except ImportError:
        sys.exit("PyMuPDF not installed. Run: pip install pymupdf")

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f"not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.pages:
        indices = [int(p) - 1 for p in args.pages.split(",")]
    elif args.start or args.end:
        start = (args.start - 1) if args.start else 0
        end = args.end if args.end else doc.page_count
        indices = list(range(start, end))
    else:
        indices = list(range(doc.page_count))

    rendered = 0
    for i in indices:
        if i < 0 or i >= doc.page_count:
            print(f"skip out-of-range page {i + 1} (deck has {doc.page_count} pages)")
            continue
        pix = doc[i].get_pixmap(dpi=args.dpi)
        out = outdir / f"p{i + 1:02d}.png"
        pix.save(str(out))
        print(out)
        rendered += 1

    print(f"\n{doc.page_count} total pages in deck. Rendered {rendered} page(s) to {outdir}/")
    print("Next: use the Read tool on each PNG above to visually check for overflow,")
    print("clipped content, wrapped headers, or near-blank continuation pages.")


if __name__ == "__main__":
    main()
