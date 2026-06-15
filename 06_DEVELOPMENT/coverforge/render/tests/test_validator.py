# tests/test_validator.py
from PIL import Image
from render.pdf_export import export_pdf
from render.validator import validate_pdf

def _pdf(tmp_path, w, h):
    p = tmp_path / "c.pdf"
    export_pdf(Image.new("RGB", (w, h), (0, 0, 0)), str(p), dpi=300)
    return str(p)

def test_correct_size_passes(tmp_path):
    ok, problems = validate_pdf(_pdf(tmp_path, 1800, 2775), 1800, 2775, dpi=300)
    assert ok and problems == []

def test_wrong_size_fails_with_reason(tmp_path):
    ok, problems = validate_pdf(_pdf(tmp_path, 1801, 2775), 1200, 1600, dpi=300)
    assert not ok
    assert any("width" in p for p in problems)
    assert any("height" in p for p in problems)

def test_within_tolerance_passes_but_just_over_fails(tmp_path):
    # 1 px at 300 dpi = 0.24 pt (inside 2 pt tol); 10 px = 2.4 pt (outside)
    ok_near, _ = validate_pdf(_pdf(tmp_path, 1801, 2775), 1800, 2775, dpi=300)
    assert ok_near
    ok_far, probs = validate_pdf(_pdf(tmp_path, 1810, 2775), 1800, 2775, dpi=300)
    assert not ok_far and any("width" in p for p in probs)
