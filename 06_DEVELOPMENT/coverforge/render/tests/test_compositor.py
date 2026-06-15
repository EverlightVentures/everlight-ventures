# tests/test_compositor.py
from PIL import Image
from render.compositor import compose_front

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
