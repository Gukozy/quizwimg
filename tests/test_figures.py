import pytest

fitz = pytest.importorskip("fitz")

from quizwimg import figures


@pytest.fixture
def sample_pdf(tmp_path):
    """Two-page PDF: text + a drawn red rectangle + one embedded 120x90 image."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "quizwimg test page")
    page.draw_rect(fitz.Rect(100, 200, 300, 350), color=(0, 0, 1), fill=(1, 0, 0))
    pm = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 90), False)
    pm.clear_with(128)
    page.insert_image(fitz.Rect(350, 200, 470, 290), pixmap=pm)
    doc.new_page(width=595, height=842).insert_text((72, 100), "page two")
    pdf = tmp_path / "doc.pdf"
    doc.save(pdf)
    doc.close()
    return pdf


def _png_size(path):
    pix = fitz.Pixmap(str(path))
    return pix.width, pix.height


def test_parse_pages():
    assert figures.parse_pages(None, 5) == [0, 1, 2, 3, 4]
    assert figures.parse_pages("1,3-4", 5) == [0, 2, 3]
    with pytest.raises(ValueError):
        figures.parse_pages("9", 5)
    with pytest.raises(ValueError):
        figures.parse_pages("abc", 5)


def test_parse_clip():
    assert figures.parse_clip("3:28,38.5,567,500") == (2, (28.0, 38.5, 567.0, 500.0))
    with pytest.raises(ValueError):
        figures.parse_clip("3:28,38")
    with pytest.raises(ValueError):
        figures.parse_clip("3:100,100,50,200")  # x1 <= x0


def test_extract_embedded(sample_pdf, tmp_path):
    out_dir = tmp_path / "figs"
    saved = figures.extract_embedded(sample_pdf, out_dir)

    assert len(saved) == 1
    assert saved[0].stat().st_size > 0
    assert _png_size(saved[0]) == (120, 90)


def test_extract_embedded_min_size_filters(sample_pdf, tmp_path):
    saved = figures.extract_embedded(sample_pdf, tmp_path / "figs", min_size=500)
    assert saved == []


def test_render_pages(sample_pdf, tmp_path):
    saved = figures.render_pages(sample_pdf, tmp_path / "pages", pages=[0], zoom=2.0)

    assert len(saved) == 1
    width, height = _png_size(saved[0])
    assert (width, height) == (1190, 1684)  # 595x842 at 2x


def test_crop_single_region(sample_pdf, tmp_path):
    out = tmp_path / "crop.png"
    figures.crop_regions(sample_pdf, [(0, (100, 200, 300, 350))], out, zoom=2.0)

    assert _png_size(out) == (400, 300)  # 200x150 points at 2x


def test_crop_regions_stitched_across_pages(sample_pdf, tmp_path):
    pytest.importorskip("PIL")
    out = tmp_path / "stitched.png"
    figures.crop_regions(
        sample_pdf,
        [(0, (100, 200, 300, 350)), (1, (100, 80, 300, 130))],
        out,
        zoom=2.0,
    )

    width, height = _png_size(out)
    assert width == 400
    assert height == 300 + 100  # vertical stitch of both crops
