"""PDF figure extraction — get the actual figures out of source documents.

Requires the ``pdf`` extra: ``pip install 'quizwimg[pdf]'`` (PyMuPDF + Pillow).

Three patterns, consolidated from real quiz-building sessions:

- :func:`extract_embedded` — pull embedded raster images (photos, scans)
  straight out of the PDF, at original resolution.
- :func:`render_pages` — render whole pages to PNG, for visual reading or
  as crop sources.
- :func:`crop_regions` — render one or more page regions (PDF point
  coordinates) and stitch them vertically into a single image. This is how
  you capture a chart, a table, or a question that spans a page break.
"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path


def _require_fitz():
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise SystemExit(
            "PyMuPDF is required for figure extraction — "
            "install with: pip install 'quizwimg[pdf]'"
        )
    return fitz


def _require_pil_image():
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit(
            "Pillow is required for stitching regions — "
            "install with: pip install 'quizwimg[pdf]'"
        )
    return Image


def parse_pages(spec, page_count):
    """Parse a 1-based page spec like ``"1,3,5-7"`` into sorted 0-based indices.

    ``None`` or ``""`` means all pages."""
    if not spec:
        return list(range(page_count))
    pages = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise ValueError(f"bad page spec part: {part!r} (expected e.g. '1,3,5-7')")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        if start < 1 or end < start:
            raise ValueError(f"bad page range: {part!r}")
        for p in range(start, end + 1):
            if p > page_count:
                raise ValueError(f"page {p} out of range (document has {page_count} pages)")
            pages.add(p - 1)
    return sorted(pages)


def parse_clip(spec):
    """Parse ``"PAGE:X0,Y0,X1,Y1"`` (1-based page, PDF points) into
    ``(page_index, (x0, y0, x1, y1))``."""
    m = re.fullmatch(
        r"(\d+):(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)", str(spec).strip()
    )
    if not m:
        raise ValueError(f"bad clip spec: {spec!r} (expected 'PAGE:X0,Y0,X1,Y1')")
    page = int(m.group(1))
    if page < 1:
        raise ValueError(f"bad clip page: {spec!r}")
    x0, y0, x1, y1 = (float(m.group(i)) for i in range(2, 6))
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"empty clip box: {spec!r}")
    return page - 1, (x0, y0, x1, y1)


def extract_embedded(pdf_path, out_dir, pages=None, min_size=64):
    """Save embedded raster images from ``pdf_path`` into ``out_dir``.

    ``pages`` is a list of 0-based page indices (default: all). Images
    smaller than ``min_size`` in either dimension are skipped (icons,
    bullets, logos). Returns the saved paths."""
    fitz = _require_fitz()
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    saved = []
    seen_xrefs = set()
    try:
        page_indices = pages if pages is not None else range(len(doc))
        for pno in page_indices:
            for img in doc[pno].get_images(full=True):
                xref = img[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                info = doc.extract_image(xref)
                if info["width"] < min_size or info["height"] < min_size:
                    continue
                out = out_dir / f"page{pno + 1:03d}_img{xref}.{info['ext']}"
                out.write_bytes(info["image"])
                saved.append(out)
    finally:
        doc.close()
    return saved


def render_pages(pdf_path, out_dir, pages=None, zoom=2.0):
    """Render pages to PNG at ``zoom``× (2.0 ≈ 144 dpi). Returns saved paths."""
    fitz = _require_fitz()
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    saved = []
    try:
        page_indices = pages if pages is not None else range(len(doc))
        matrix = fitz.Matrix(zoom, zoom)
        for pno in page_indices:
            pix = doc[pno].get_pixmap(matrix=matrix, alpha=False)
            out = out_dir / f"{pdf_path.stem}_p{pno + 1:03d}.png"
            pix.save(out)
            saved.append(out)
    finally:
        doc.close()
    return saved


def crop_regions(pdf_path, clips, out_path, zoom=2.0):
    """Render region(s) of ``pdf_path`` into a single PNG at ``out_path``.

    ``clips`` is a list of ``(page_index, (x0, y0, x1, y1))`` tuples with
    0-based pages and PDF-point coordinates. A single clip is saved
    directly; multiple clips are stitched vertically (centered, white
    background) — the pattern for figures or questions that span a page
    break. Returns ``out_path``."""
    fitz = _require_fitz()
    pdf_path = Path(pdf_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not clips:
        raise ValueError("clips must be non-empty")

    doc = fitz.open(pdf_path)
    try:
        matrix = fitz.Matrix(zoom, zoom)
        pixmaps = []
        for pno, bbox in clips:
            clip = fitz.Rect(*bbox)
            pix = doc[pno].get_pixmap(matrix=matrix, clip=clip, alpha=False)
            if pix.width == 0 or pix.height == 0:
                raise ValueError(f"empty crop: page {pno + 1}, bbox {bbox}")
            pixmaps.append(pix)

        if len(pixmaps) == 1:
            pixmaps[0].save(out_path)
            return out_path

        Image = _require_pil_image()
        parts = [Image.open(BytesIO(p.tobytes("png"))).convert("RGB") for p in pixmaps]
        width = max(part.width for part in parts)
        height = sum(part.height for part in parts)
        combined = Image.new("RGB", (width, height), "white")
        y = 0
        for part in parts:
            combined.paste(part, ((width - part.width) // 2, y))
            y += part.height
        combined.save(out_path, optimize=True)
        return out_path
    finally:
        doc.close()
