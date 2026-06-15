# tests/test_pdf_export.py
from PIL import Image
from pypdf import PdfReader
from render.pdf_export import export_pdf

def test_pdf_page_size_matches_pixels_at_300dpi(tmp_path):
    img = Image.new("RGB", (1800, 2775), (0, 0, 0))  # 6x9.25 in at 300 dpi
    out = tmp_path / "wrap.pdf"
    export_pdf(img, str(out), dpi=300)
    page = PdfReader(str(out)).pages[0]
    # PDF points = inches * 72; 1800/300*72 = 432, 2775/300*72 = 666
    assert round(float(page.mediabox.width)) == 432
    assert round(float(page.mediabox.height)) == 666
