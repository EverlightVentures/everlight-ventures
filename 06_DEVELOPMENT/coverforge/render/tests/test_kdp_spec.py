# tests/test_kdp_spec.py
import pytest
from render.kdp_spec import spine_width_in, cover_dimensions, ebook_dimensions, PAPER_FACTOR

def test_spine_white_200pg():
    assert spine_width_in(200, "white") == pytest.approx(200 * 0.002252)

def test_spine_rejects_unknown_paper():
    with pytest.raises(ValueError):
        spine_width_in(200, "papyrus")

def test_cover_dimensions_6x9_200pg_white():
    d = cover_dimensions((6.0, 9.0), 200, "white", dpi=300, bleed=0.125)
    # full wrap = 2*6 + spine + 2*0.125 inches, height = 9 + 0.25 inches
    assert d.full_w_px == round((12 + 200 * 0.002252 + 0.25) * 300)
    assert d.full_h_px == round(9.25 * 300)
    assert d.spine_px == round(200 * 0.002252 * 300)
    # panels tile the full width exactly (no gap)
    assert d.back_w_px + d.spine_px + d.front_w_px == d.full_w_px

def test_ebook_is_recommended_1600x2560():
    assert ebook_dimensions() == (1600, 2560)
