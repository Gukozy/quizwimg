"""quizwimg command-line interface.

    quizwimg build --config quiz.json --out quiz.html [--lang ko]
    quizwimg extract embedded doc.pdf --out-dir figures/
    quizwimg extract pages doc.pdf --out-dir pages/ --pages 3-7
    quizwimg extract region doc.pdf --clip 3:28,120,567,430 --out fig.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quizwimg import builder, figures


def _cmd_build(ns):
    if not ns.config.exists():
        sys.exit(f"config not found: {ns.config}")
    template = ns.template or builder.DEFAULT_TEMPLATE
    if not template.exists():
        sys.exit(f"template not found: {template}")
    builder.build(ns.config, ns.out, template, lang=ns.lang)


def _open_page_count(pdf_path):
    fitz = figures._require_fitz()
    if not pdf_path.exists():
        sys.exit(f"pdf not found: {pdf_path}")
    doc = fitz.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()


def _cmd_extract_embedded(ns):
    pages = figures.parse_pages(ns.pages, _open_page_count(ns.pdf))
    saved = figures.extract_embedded(ns.pdf, ns.out_dir, pages=pages, min_size=ns.min_size)
    for p in saved:
        print(p)
    print(f"extracted: {len(saved)} image(s) → {ns.out_dir}")


def _cmd_extract_pages(ns):
    pages = figures.parse_pages(ns.pages, _open_page_count(ns.pdf))
    saved = figures.render_pages(ns.pdf, ns.out_dir, pages=pages, zoom=ns.zoom)
    for p in saved:
        print(p)
    print(f"rendered: {len(saved)} page(s) → {ns.out_dir}")


def _cmd_extract_region(ns):
    try:
        clips = [figures.parse_clip(spec) for spec in ns.clip]
    except ValueError as exc:
        sys.exit(str(exc))
    if not ns.pdf.exists():
        sys.exit(f"pdf not found: {ns.pdf}")
    out = figures.crop_regions(ns.pdf, clips, ns.out, zoom=ns.zoom)
    print(f"cropped: {len(clips)} region(s) → {out}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="quizwimg",
        description="Build offline single-file HTML quizzes — with figures from your PDFs.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build a quiz HTML from a JSON config")
    b.add_argument("--config", required=True, type=Path)
    b.add_argument("--out", required=True, type=Path)
    b.add_argument("--template", type=Path, default=None)
    b.add_argument("--lang", default=None, help="UI language (en, ko); overrides config")
    b.set_defaults(func=_cmd_build)

    ex = sub.add_parser("extract", help="extract figures from a PDF (requires quizwimg[pdf])")
    exsub = ex.add_subparsers(dest="extract_command", required=True)

    emb = exsub.add_parser("embedded", help="save embedded raster images")
    emb.add_argument("pdf", type=Path)
    emb.add_argument("--out-dir", required=True, type=Path)
    emb.add_argument("--pages", default=None, help='1-based pages, e.g. "1,3,5-7" (default: all)')
    emb.add_argument("--min-size", type=int, default=64,
                     help="skip images smaller than this in either dimension (default: 64)")
    emb.set_defaults(func=_cmd_extract_embedded)

    pg = exsub.add_parser("pages", help="render whole pages to PNG")
    pg.add_argument("pdf", type=Path)
    pg.add_argument("--out-dir", required=True, type=Path)
    pg.add_argument("--pages", default=None, help='1-based pages, e.g. "1,3,5-7" (default: all)')
    pg.add_argument("--zoom", type=float, default=2.0, help="render scale (2.0 ≈ 144 dpi)")
    pg.set_defaults(func=_cmd_extract_pages)

    rg = exsub.add_parser(
        "region",
        help="crop page region(s) into one PNG; repeat --clip to stitch vertically",
    )
    rg.add_argument("pdf", type=Path)
    rg.add_argument("--clip", action="append", required=True, metavar="PAGE:X0,Y0,X1,Y1",
                    help="1-based page + PDF-point bbox; repeatable")
    rg.add_argument("--out", required=True, type=Path)
    rg.add_argument("--zoom", type=float, default=2.0, help="render scale (2.0 ≈ 144 dpi)")
    rg.set_defaults(func=_cmd_extract_region)

    ns = ap.parse_args(argv)
    ns.func(ns)


if __name__ == "__main__":
    main()
