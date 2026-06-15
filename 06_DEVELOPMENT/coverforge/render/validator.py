# render/validator.py
"""Refuse to ship a file Amazon would reject. Compares PDF page size (points)
against the pixel target at the given DPI, within a small rounding tolerance."""
from pypdf import PdfReader

def validate_pdf(pdf_path: str, expect_w_px: int, expect_h_px: int,
                 dpi: int = 300, tol_pt: float = 2.0):
    page = PdfReader(pdf_path).pages[0]
    want_w = expect_w_px / dpi * 72
    want_h = expect_h_px / dpi * 72
    problems = []
    if abs(float(page.mediabox.width) - want_w) > tol_pt:
        problems.append(f"width off: got {float(page.mediabox.width):.1f}pt want {want_w:.1f}pt")
    if abs(float(page.mediabox.height) - want_h) > tol_pt:
        problems.append(f"height off: got {float(page.mediabox.height):.1f}pt want {want_h:.1f}pt")
    return (len(problems) == 0, problems)
