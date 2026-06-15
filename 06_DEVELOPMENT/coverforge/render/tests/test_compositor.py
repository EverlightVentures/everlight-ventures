# tests/test_compositor.py
from PIL import Image
from render.compositor import compose_front, compose_wrap
from render.kdp_spec import cover_dimensions

def _bg(w, h):
    return Image.new("RGB", (w, h), (10, 10, 10))

def test_front_panel_is_exact_target_size():
    out = compose_front(_bg(400, 600), "MIDNIGHT", "A. Author", (400, 600))
    assert out.size == (400, 600)
    assert out.mode == "RGB"

def test_front_panel_actually_draws_text():
    target = (400, 600)
    blank = _bg(*target)
    out = compose_front(blank, "MIDNIGHT", "A. Author", target)
    # at least some pixels changed vs the blank background => text was drawn
    assert out.tobytes() != blank.tobytes()

def test_wrap_is_exact_full_size_and_tiles_panels():
    d = cover_dimensions((6.0, 9.0), 200, "white")
    bg = Image.new("RGB", (d.full_w_px, d.full_h_px), (20, 20, 20))
    wrap = compose_wrap(bg, "MIDNIGHT", "A. Author", "Back blurb here.", d)
    assert wrap.size == (d.full_w_px, d.full_h_px)
    # front region must have title/author composited over it (not a plain panel)
    front_x = d.back_w_px + d.spine_px
    front_region = wrap.crop((front_x, 0, d.full_w_px, d.full_h_px))
    assert front_region.size == (d.front_w_px, d.full_h_px)
    plain = Image.new("RGB", (d.front_w_px, d.full_h_px), (20, 20, 20))
    assert front_region.tobytes() != plain.tobytes()  # title/author were drawn
